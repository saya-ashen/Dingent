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
import {
  useMarketItems,
  useMarketDownload,
} from "@/features/market/hooks/use-market-data";
import { MarketItem } from "@/types/entity";

export default function MarketPage() {
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi();
  const wsApi = api.forWorkspace(slug);
  const qc = useQueryClient();

  const { filters } = useMarketFilters();
  const { filteredItems, isLoading, error } = useMarketItems(slug, filters);
  const downloadMutation = useMarketDownload(slug);

  const handleDownload = (item: MarketItem) => {
    downloadMutation.mutate({
      item_id: item.id,
      category: item.category, // 假设 MarketItem 中包含 category 字段，或者根据 filters.category 传入
      isUpdate: item.update_available || false,
    });
  };

  const renderContent = () => {
    if (isLoading) {
      return <LoadingSkeleton lines={5} />;
    }

    if (error) {
      return (
        <div className="flex h-40 items-center justify-center text-red-500 bg-red-50/50 rounded-lg border border-red-100">
          Failed to load market items. Please try again later.
        </div>
      );
    }

    if (filteredItems.length === 0) {
      return (
        <EmptyState
          title="No items found"
          description="Try adjusting your filters or search terms."
        />
      );
    }

    return (
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
    );
  };

  return (
    <PageContainer
      title="Marketplace Integrations"
      description="Browse plugins, assistants, and workflows from the community marketplace."
    >
      <MarketToolbar />
      <Separator className="shadow-sm my-4" /> {/* 增加一点 margin */}
      <div className="min-h-[200px]">{renderContent()}</div>
    </PageContainer>
  );
}
