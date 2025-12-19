"use client";

import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/utils";
import { getClientApi } from "@/lib/api/client";
import { Separator } from "@/components/ui/separator";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { useMarketFilters } from "@/features/market/hooks/use-market-filters";
import { MarketToolbar } from "@/features/market/components/market-toolbar";
import { MarketCard } from "@/features/market/components/market-card";
import { PageContainer } from "@/components/common/page-container";


export default function MarketPage() {
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi();
  const wsApi = api.forWorkspace(slug);
  const qc = useQueryClient();

  const { filters } = useMarketFilters();


  const itemsQuery = useQuery({
    queryKey: ["market-items", filters.category], // key 随 URL 参数变化
    queryFn: () => wsApi.market.list(filters.category),
    staleTime: 60_000,
  });

  const downloadMutation = useMutation({
    mutationFn: wsApi.market.download,
    onSuccess: (_data, variables) => {
      const action = variables.isUpdate ? "updated" : "downloaded";
      toast.success(`Successfully ${action} ${variables.category}`);
      // 更加精准的 invalidation
      qc.invalidateQueries({ queryKey: ["market-items"] });
      qc.invalidateQueries({ queryKey: ["market-metadata"] });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Operation failed")),
  });

  const filteredItems = useMemo(() => {
    if (!itemsQuery.data) return [];

    let result = [...itemsQuery.data];
    const term = filters.search.toLowerCase();

    // 搜索过滤
    if (term) {
      result = result.filter(
        (item) =>
          item.name.toLowerCase().includes(term) ||
          item.description?.toLowerCase().includes(term) ||
          item.tags?.some((t) => t.toLowerCase().includes(term))
      );
    }

    // 排序
    result.sort((a, b) =>
      filters.sort === "asc"
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name)
    );

    return result;
  }, [itemsQuery.data, filters.search, filters.sort]);

  // --- Handlers ---
  const handleDownload = (item: any) => {
    downloadMutation.mutate({
      item_id: item.id,
      category: item.category,
      isUpdate: item.update_available || false,
    });
  };

  return (
    <PageContainer title="Marketplace Integrations" description="Browse plugins, assistants, and workflows from the community marketplace.">
      <MarketToolbar />
      <Separator className="shadow-sm" />
      <div className="min-h-[200px]">
        {itemsQuery.isLoading ? (
          <LoadingSkeleton lines={5} />
        ) : itemsQuery.error ? (
          <div className="text-red-600">Failed to load market items.</div>
        ) : filteredItems.length === 0 ? (
          <EmptyState title="No items found" />
        ) : (
          <div className="grid gap-4 pb-16 sm:grid-cols-2 lg:grid-cols-3">
            {filteredItems.map((item) => (
              <MarketCard
                key={item.id}
                item={item}
                onDownload={handleDownload}
                isProcessing={
                  downloadMutation.isPending &&
                  downloadMutation.variables?.item_id === item.id
                }
              />
            ))}
          </div>
        )}

      </div>
    </PageContainer>


  );
}
