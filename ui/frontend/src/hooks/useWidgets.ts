import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";
import { Widget } from "@/types";

type AgentState = { tool_output_ids: string[] };


interface FetchedResource {
    id?: string;
    payloads?: unknown[];
    metadata?: unknown;
    [k: string]: unknown;
}

interface UseResourceWidgetsOptions {
    clearOnEmptyIds?: boolean;
    autoFetch?: boolean;
    keepOrphanWidgets?: boolean;
}

interface UseResourceWidgetsResult {
    widgets: Widget[];
    loadingIds: string[];
    errorById: Record<string, string>;
    refresh: (ids?: string[] | "all") => void;
    hasFetched: boolean;
}

/**
 * 底层：可接收外部传入的 id 列表
 */
export function useResourceWidgets(
    ids: string[],
    {
        clearOnEmptyIds = true,
        autoFetch = true,
        keepOrphanWidgets = false,
    }: UseResourceWidgetsOptions = {}
): UseResourceWidgetsResult {
    const [widgetsById, setWidgetsById] = useState<Record<string, Widget[]>>({});
    const [loadingIds, setLoadingIds] = useState<string[]>([]);
    const [errorById, setErrorById] = useState<Record<string, string>>({});
    const fetchedIdsRef = useRef<Set<string>>(new Set());
    const abortControllers = useRef<Record<string, AbortController>>({});
    const hasFetchedRef = useRef(false);

    const normalizedIds = useMemo(
        () => Array.from(new Set(ids.filter(Boolean))),
        [ids]
    );

    const removeWidgetsNotInIds = useCallback(() => {
        if (keepOrphanWidgets) return;
        setWidgetsById(prev => {
            const next: Record<string, Widget[]> = {};
            for (const id of normalizedIds) {
                if (prev[id]) next[id] = prev[id];
            }
            return next;
        });
    }, [normalizedIds, keepOrphanWidgets]);

    const fetchOne = useCallback(
        async (id: string, force = false) => {
            if (!force && fetchedIdsRef.current.has(id)) return;

            // cancel ongoing fetch for same id
            if (abortControllers.current[id]) {
                abortControllers.current[id].abort();
            }
            const controller = new AbortController();
            abortControllers.current[id] = controller;

            setLoadingIds(prev => (prev.includes(id) ? prev : [...prev, id]));
            setErrorById(prev => {
                const { [id]: _, ...rest } = prev;
                return rest;
            });

            try {
                const res = await fetch(`/api/resource/${id}`, {
                    signal: controller.signal,
                });
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }
                const resource = (await res.json()) as FetchedResource;
                if (!resource || !Array.isArray(resource.payloads)) {
                    throw new Error("Invalid resource payloads structure");
                }

                const widgets: Widget[] = resource.payloads.map((item) => {
                    const payload = item as Partial<WidgetPayload> & Record<string, unknown>;
                    const type = typeof payload.type === "string" ? payload.type : "markdown";
                    return {
                        id,
                        type,
                        payload: {
                            ...(payload as WidgetPayload),
                            type,
                        },
                        metadata: resource.metadata,
                    };
                });

                setWidgetsById(prev => ({ ...prev, [id]: widgets }));
                fetchedIdsRef.current.add(id);
                hasFetchedRef.current = true;
            } catch (err: any) {
                if (err?.name === "AbortError") return;
                setErrorById(prev => ({ ...prev, [id]: err?.message || "Unknown fetch error" }));
            } finally {
                setLoadingIds(prev => prev.filter(x => x !== id));
                delete abortControllers.current[id];
            }
        },
        []
    );

    const refresh = useCallback(
        (target: string[] | "all" = "all") => {
            const targetIds =
                target === "all" ? normalizedIds : target.filter(id => normalizedIds.includes(id));
            for (const id of targetIds) {
                fetchedIdsRef.current.delete(id);
            }
            targetIds.forEach(id => { void fetchOne(id, true); });
        },
        [normalizedIds, fetchOne]
    );

    // auto fetch
    useEffect(() => {
        if (normalizedIds.length === 0) {
            if (clearOnEmptyIds) {
                setWidgetsById(prev => {
                    if (Object.keys(prev).length === 0) return prev; // 幂等
                    return {};
                });
                if (fetchedIdsRef.current.size > 0) {
                    fetchedIdsRef.current.clear();
                }
            }
            return;
        }

        removeWidgetsNotInIds();

        if (!autoFetch) return;

        for (const id of normalizedIds) {
            if (!fetchedIdsRef.current.has(id)) {
                void fetchOne(id);
            }
        }
    }, [
        normalizedIds,
        autoFetch,
        clearOnEmptyIds,
        removeWidgetsNotInIds,
        fetchOne,
    ]);

    // cleanup
    useEffect(() => {
        return () => {
            Object.values(abortControllers.current).forEach(c => c.abort());
        };
    }, []);

    const widgets = useMemo(() => {
        const list: Widget[] = [];
        for (const id of normalizedIds) {
            const arr = widgetsById[id];
            if (arr) list.push(...arr);
        }
        return list;
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
 * 对外暴露的最终 Hook：
 * 自动从 agent state 中读取 tool_output_ids
 */
export function useWidgets() {
    const { state } = useCoAgent<AgentState>({ name: "sample_agent", });
    const ids = state?.tool_output_ids || [];
    console.log("state", state)
    return useResourceWidgets(ids);
}
