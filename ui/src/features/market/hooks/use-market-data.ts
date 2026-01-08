import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getClientApi } from "@/lib/api/client";
import { getErrorMessage } from "@/lib/utils";
import { MarketFilters } from "./use-market-filters";

// 统一管理 Query Keys
export const marketKeys = {
  all: ["market-items"] as const,
  list: (workspaceSlug: string, category: string) =>
    [...marketKeys.all, workspaceSlug, category] as const,
  metadata: ["market-metadata"] as const,
};

export function useMarketItems(workspaceSlug: string, filters: MarketFilters) {
  // 1. Memoize API Client
  const api = useMemo(
    () => getClientApi().forWorkspace(workspaceSlug),
    [workspaceSlug],
  );

  // 2. Query
  const query = useQuery({
    queryKey: marketKeys.list(workspaceSlug, filters.category),
    queryFn: () => api.market.list(filters.category),
    staleTime: 60_000,
  });

  // 3. 过滤与排序逻辑 (在此处处理，保持 UI 纯净)
  const filteredItems = useMemo(() => {
    if (!query.data) return [];

    let result = [...query.data];
    const term = filters.search.toLowerCase();

    if (term) {
      result = result.filter(
        (item) =>
          item.name.toLowerCase().includes(term) ||
          item.description?.toLowerCase().includes(term) ||
          item.tags?.some((t) => t.toLowerCase().includes(term)),
      );
    }

    result.sort((a, b) =>
      filters.sort === "asc"
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name),
    );

    return result;
  }, [query.data, filters.search, filters.sort]);

  return { ...query, filteredItems };
}

export function useMarketDownload(workspaceSlug: string) {
  const qc = useQueryClient();
  const api = useMemo(
    () => getClientApi().forWorkspace(workspaceSlug),
    [workspaceSlug],
  );

  return useMutation({
    mutationFn: (variables: any) => api.market.download(variables),
    onSuccess: (_data, variables) => {
      const action = variables.isUpdate ? "updated" : "downloaded";
      toast.success(`Successfully ${action} ${variables.category}`);

      qc.invalidateQueries({ queryKey: marketKeys.all });
      qc.invalidateQueries({ queryKey: marketKeys.metadata });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Operation failed")),
  });
}
