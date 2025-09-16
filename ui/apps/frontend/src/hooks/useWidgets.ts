import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";
import { Widget } from "@/types";

type AgentState = { artifact_ids?: string[] };

/**
 * 后端格式
 * 示例：
 * {
 *   "version": "1.0",
 *   "display": [
 *     {
 *       "type": "table",
 *       "columns": [...],
 *       "rows": [...],
 *       "title": "top stories"
 *     }
 *   ],
 *   "data": null,
 *   "metadata": {}
 * }
 */
interface DisplayItem {
    type?: string;
    title?: string;
    columns?: string[];
    rows?: unknown[];
    content?: string;
    [k: string]: unknown;
}

interface ResourceResponse {
    version?: string;
    display: DisplayItem[];
    data?: unknown;
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

const widgetFactory = {
    createWidget: (item: DisplayItem, resourceId: string, index: number): Widget => {
        const widgetId = `${resourceId}::${index}`;
        const baseProps = {
            id: widgetId,
            metadata: item.metadata,
        };

        switch (item.type) {
            case 'table':
                return {
                    ...baseProps,
                    type: 'table',
                    payload: {
                        type: 'table',
                        title: item.title,
                        columns: Array.isArray(item.columns) ? item.columns : [],
                        rows: Array.isArray(item.rows) ? item.rows : [],
                    },
                };
            // 在这里可以增加其他类型的 widget
            default:
                return {
                    ...baseProps,
                    type: 'markdown',
                    payload: {
                        type: 'markdown',
                        content: item.content || '',
                        title: "" + (item.title || 'Display'),
                    },
                };
        }
    }
};
/**
 * 内部 Hook：支持 ids 为 undefined（表示“这次调用不想改变已有 ids”）
 */
export function useResourceWidgets(
    ids?: string[] | null,
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

    // ids 为 undefined -> 不变更
    const normalizedIds = useMemo(() => {
        if (!ids) return undefined;
        return Array.from(new Set(ids.filter(Boolean)));
    }, [ids]);

    const removeWidgetsNotInIds = useCallback(() => {
        if (keepOrphanWidgets) return;
        if (!normalizedIds) return;
        setWidgetsById(prev => {
            const next: Record<string, Widget[]> = {};
            for (const id of normalizedIds) {
                if (prev[id]) next[id] = prev[id];
            }
            return next;
        });
    }, [normalizedIds, keepOrphanWidgets]);

    const buildWidgets = useCallback(
        (resource: ResourceResponse, resourceId: string): Widget[] => {
            if (!Array.isArray(resource.display)) {
                throw new Error("Invalid response: 'display' must be an array");
            }
            return resource.display.map((item, index) => widgetFactory.createWidget(item, resourceId, index));
        },
        []
    );

    const fetchOne = useCallback(
        async (id: string, force = false) => {
            if (!force && fetchedIdsRef.current.has(id)) return;

            // 取消同 id 正在进行的请求
            if (abortControllers.current[id]) {
                abortControllers.current[id].abort();
            }
            const controller = new AbortController();
            abortControllers.current[id] = controller;

            setLoadingIds(prev => (prev.includes(id) ? prev : [...prev, id]));
            setErrorById(prev => {
                const { [id]: _omit, ...rest } = prev;
                return rest;
            });

            try {
                const res = await fetch(`/api/resource/${id}`, { signal: controller.signal });
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }
                const resource = (await res.json()) as ResourceResponse;

                const widgets = buildWidgets(resource, id);
                setWidgetsById(prev => ({ ...prev, [id]: widgets }));
                fetchedIdsRef.current.add(id);
                hasFetchedRef.current = true;
            } catch (err: unknown) {
                if (err instanceof Error && err.name === "AbortError") {
                    return;
                }
                let errorMessage = "Unknown fetch error";
                if (err instanceof Error) {
                    errorMessage = err.message;
                }
                setErrorById(prev => ({ ...prev, [id]: errorMessage }));
            } finally {
                setLoadingIds(prev => prev.filter(x => x !== id));
                delete abortControllers.current[id];
            }
        },
        [buildWidgets]
    );

    const refresh = useCallback(
        (target: string[] | "all" = "all") => {
            if (!normalizedIds || normalizedIds.length === 0) return;
            const targetIds =
                target === "all" ? normalizedIds : target.filter(id => normalizedIds.includes(id));
            for (const id of targetIds) {
                fetchedIdsRef.current.delete(id);
            }
            targetIds.forEach(id => { void fetchOne(id, true); });
        },
        [normalizedIds, fetchOne]
    );

    // 自动拉取逻辑
    useEffect(() => {
        // undefined：保持现状，不清空不加载
        if (normalizedIds === undefined) return;

        if (normalizedIds.length === 0) {
            if (clearOnEmptyIds) {
                setWidgetsById(prev => {
                    if (Object.keys(prev).length === 0) return prev;
                    return {};
                });
                fetchedIdsRef.current.clear();
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

    // 卸载时中止所有请求
    useEffect(() => {
        return () => {
            Object.values(abortControllers.current).forEach(c => c.abort());
        };
    }, []);

    const widgets = useMemo(() => {
        if (normalizedIds === undefined) {
            // 未提供新的 ids，返回当前全部
            return Object.values(widgetsById).flat();
        }
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
 * 对外 Hook：从 agent state 里读取 artifact_ids
 * - 没有该字段 => 传 undefined，不触发重置
 * - 字段存在 (可为空数组) => 按值传递
 */
export function useWidgets() {
    const { state } = useCoAgent<AgentState>({ name: "dingent" });
    const ids = state && Object.prototype.hasOwnProperty.call(state, "artifact_ids")
        ? state.artifact_ids
        : undefined;

    return useResourceWidgets(ids);
}
