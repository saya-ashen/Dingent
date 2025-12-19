"use client";

import { PageHeader } from "@/components/common/page-header"; // 复用组件
import { ErrorDisplay } from "@/components/common/error-display"; // 复用组件
import { useWorkspaceApi } from "@/hooks/use-workspace-api"; // 复用 Hook
import { useOverviewQuery } from "@/features/overview/hooks/use-overview";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { AssistantsCard } from "@/features/overview/components/assistants-card";
import { RecentLogsCard } from "@/features/overview/components/recent-logs-card";
import { PluginsCard } from "@/features/overview/components/plugins-card";
import { LlmCard } from "@/features/overview/components/llm-card";
import { AnalyticsTab } from "@/features/dashboard/analytics-tab";
import { DashboardStats } from "@/features/overview/components/dashboard-stats";
import { OverviewMarketCard } from "@/features/overview/components/market-card";
import { PageContainer } from "@/components/common/page-container";

export default function DashboardPage() {
  const { data, isLoading, error, refetch } = useOverviewQuery();
  const { api } = useWorkspaceApi();


  if (isLoading) {
    return (
      <>
        <PageHeader heading="Dashboard" />
        <LoadingSkeleton lines={5} />
      </>
    );
  }

  if (error || !data) {
    return (
      <>
        <PageHeader heading="Dashboard" />
        <ErrorDisplay onRetry={() => refetch()} />
      </>
    );
  }

  return (
    <PageContainer
      title="Assistant Configuration"
      description="Manage assistants, plugins, and tool configurations."
      action={
        <Button onClick={() => refetch()} variant="outline" size="sm">
          Refresh
        </Button>
      }>

      <Tabs orientation="vertical" defaultValue="overview" className="space-y-4">

        <TabsContent value="overview" className="space-y-4">
          <DashboardStats stats={data} error={error !== null} />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-7">
            <div className="col-span-1 space-y-4 lg:col-span-4">
              <AssistantsCard assistants={data.assistants} error={error} />
              <RecentLogsCard logs={data.logs} />
            </div>

            <div className="col-span-1 space-y-4 lg:col-span-3">
              <PluginsCard plugins={data.plugins} />
              <LlmCard llm={data.llm} />
              <OverviewMarketCard market={data.market} loading={isLoading} />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <AnalyticsTab wsApi={api} />
        </TabsContent>
      </Tabs>
    </ PageContainer>
  );
}
