
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";
import { Widget } from "@repo/types";
import { api, Artifact, DisplayItem } from "@repo/api-client";
import { useActiveWorkflowId, useWorkflow } from "@repo/store";

type AgentState = { artifact_ids?: string[] };

const widgetFactory = {
  createWidget: (
    item: DisplayItem,
    artifactId: string,
    index: number,
  ): Widget => {
    const widgetId = `${artifactId}::${index}`;
    const baseProps = {
      id: widgetId,
      metadata: item.metadata,
    };

    switch (item.type) {
      case "table":
        return {
          ...baseProps,
          type: "table",
          payload: {
            type: "table",
            title: item.title,
            columns: Array.isArray(item.columns) ? item.columns : [],
            rows: Array.isArray(item.rows) ? item.rows : [],
          },
        };
      default:
        return {
          ...baseProps,
          type: "markdown",
          payload: {
            type: "markdown",
            content: item.content || "",
            title: "" + (item.title || "Display"),
          },
        };
    }
  },
};

/**
 * Internal hook to fetch artifacts by their IDs and transform them into widgets.
 */
export function useArtifactWidgets(
  ids?: string[] | null,
  {
    clearOnEmptyIds = true,
    autoFetch = true,
    keepOrphanWidgets = false,
  }: {
    clearOnEmptyIds?: boolean;
    autoFetch?: boolean;
    keepOrphanWidgets?: boolean;
  } = {},
): {
  widgets: Widget[];
  loadingIds: string[];
  errorById: Record<string, string>;
  refresh: (ids?: string[] | "all") => void;
  hasFetched: boolean;
} {
  const [widgetsById, setWidgetsById] = useState<Record<string, Widget[]>>({});
  const [loadingIds, setLoadingIds] = useState<string[]>([]);
  const [errorById, setErrorById] = useState<Record<string, string>>({});
  const fetchedIdsRef = useRef<Set<string>>(new Set());
  const abortControllers = useRef<Record<string, AbortController>>({});
  const hasFetchedRef = useRef(false);

  const normalizedIds = useMemo(() => {
    if (ids === undefined || ids === null) return undefined;
    return Array.from(new Set(ids.filter(Boolean)));
  }, [ids]);

  const removeWidgetsNotInIds = useCallback(() => {
    if (keepOrphanWidgets || !normalizedIds) return;
    setWidgetsById((prev) => {
      const next: Record<string, Widget[]> = {};
      for (const id of normalizedIds) {
        if (prev[id]) next[id] = prev[id];
      }
      return next;
    });
  }, [normalizedIds, keepOrphanWidgets]);

  const buildWidgets = useCallback(
    (artifact: Artifact, artifactId: string): Widget[] => {
      if (!Array.isArray(artifact.display)) {
        throw new Error("Invalid response: 'display' must be an array");
      }
      return artifact.display.map((item, index) =>
        widgetFactory.createWidget(item, artifactId, index),
      );
    },
    [],
  );

  const fetchArtifact = useCallback(
    async (id: string, force = false) => {
      if (!force && fetchedIdsRef.current.has(id)) return;

      abortControllers.current[id]?.abort();
      const controller = new AbortController();
      abortControllers.current[id] = controller;

      setLoadingIds((prev) => Array.from(new Set([...prev, id])));
      setErrorById((prev) => {
        const { [id]: _omit, ...rest } = prev;
        return rest;
      });

      try {
        // --- REFACTORED PART ---
        // Use the API client, passing the abort signal for cancellation.
        const artifact = await api.frontend.artifacts.get(id, { signal: controller.signal });

        const widgets = buildWidgets(artifact, id);
        setWidgetsById((prev) => ({ ...prev, [id]: widgets }));
        fetchedIdsRef.current.add(id);
        hasFetchedRef.current = true;
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          return; // Request was cancelled, so we do nothing.
        }
        const errorMessage = err instanceof Error ? err.message : "Failed to fetch artifact";
        setErrorById((prev) => ({ ...prev, [id]: errorMessage }));
      } finally {
        setLoadingIds((prev) => prev.filter((x) => x !== id));
        delete abortControllers.current[id];
      }
    },
    [buildWidgets],
  );

  const refresh = useCallback(
    (target: string[] | "all" = "all") => {
      if (!normalizedIds) return;
      const targetIds =
        target === "all"
          ? normalizedIds
          : target.filter((id) => normalizedIds.includes(id));

      targetIds.forEach((id) => {
        fetchedIdsRef.current.delete(id);
        void fetchArtifact(id, true);
      });
    },
    [normalizedIds, fetchArtifact],
  );

  // Auto-fetching logic (calls fetchArtifact)
  useEffect(() => {
    if (normalizedIds === undefined) return;

    if (normalizedIds.length === 0) {
      if (clearOnEmptyIds) {
        setWidgetsById({});
        fetchedIdsRef.current.clear();
      }
      return;
    }

    removeWidgetsNotInIds();

    if (autoFetch) {
      for (const id of normalizedIds) {
        if (!fetchedIdsRef.current.has(id)) {
          void fetchArtifact(id);
        }
      }
    }
  }, [
    normalizedIds,
    autoFetch,
    clearOnEmptyIds,
    removeWidgetsNotInIds,
    fetchArtifact,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      Object.values(abortControllers.current).forEach((c) => c.abort());
    };
  }, []);


  const widgets = useMemo(() => {
    if (normalizedIds === undefined) {
      return Object.values(widgetsById).flat();
    }
    return normalizedIds.flatMap((id) => widgetsById[id] || []);
  }, [widgetsById, normalizedIds]);

  return {
    widgets,
    loadingIds,
    errorById,
    refresh,
    hasFetched: hasFetchedRef.current,
  };
}

/**
 * Public hook that reads artifact_ids from the agent's state
 * and uses useArtifactWidgets to fetch and display them.
 */
export function useWidgets() {
  const { data: activeId } = useActiveWorkflowId();
  const { data: workflow } = useWorkflow(activeId ?? null);
  const { state } = useCoAgent<AgentState>({ name: workflow?.name || "unknown" });
  const ids =
    state && Object.prototype.hasOwnProperty.call(state, "artifact_ids")
      ? state.artifact_ids
      : undefined;

  // Hook renamed for clarity
  return useArtifactWidgets(ids);
}
