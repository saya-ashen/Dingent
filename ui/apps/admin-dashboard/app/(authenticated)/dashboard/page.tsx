"use client";

import { OverviewData } from "@repo/api-client";
import { useOverview } from "./useOverview";
import {
  ConfigDrawer,
  Tabs,
  TabsContent,
  Button,
  FloatingActionButtons,
  Header,
  Main,
  ProfileDropdown,
  Search,
  ThemeSwitch,
  LoadingSkeleton,
} from "@repo/ui/components";

import {
  AnalyticsTab,
  AssistantsCard,
  DashboardStats,
  LlmCard,
  MarketCard,
  PluginsCard,
  RecentLogsCard,
} from "@repo/ui/components";

export default function DashboardPage() {
  const { data, loading, error, reload } = useOverview();
  const renderContent = () => {
    if (loading) {
      return <LoadingSkeleton lines={5} />;
    }

    // 2. Handle the error or "no data" state
    if (error || !data) {
      return (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center h-[450px]">
          <h2 className="text-xl font-semibold">Could Not Load Dashboard</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            There was an issue retrieving your data. Please try again.
          </p>
          <Button onClick={reload} className="mt-4">
            Retry
          </Button>
        </div>
      );
    }

    // 3. Handle the success state (data is guaranteed to exist here)
    return <DashboardContent data={data} loading={false} error={error} />;
  };
  return (
    <>
      <Header>
        <div className="ms-auto flex items-center space-x-4">
          <Search />
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>
      <FloatingActionButtons>
        <Button variant="outline" onClick={reload} disabled={loading}>
          Refresh
        </Button>
      </FloatingActionButtons>
      <Main>
        <div className="mb-2 flex items-center justify-between space-y-2">
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        </div>
        {renderContent()}
      </Main>
    </>
  );
}
function DashboardContent({
  data,
  loading,
  error,
}: {
  data: OverviewData;
  loading: boolean;
  error: string | null;
}) {
  return (
    <Tabs orientation="vertical" defaultValue="overview" className="space-y-4">
      <div className="w-full overflow-x-auto pb-2">{/* ...TabsList... */}</div>
      <TabsContent value="overview" className="space-y-4">
        <DashboardStats stats={data} loading={loading} error={!!error} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-7">
          <div className="col-span-1 space-y-4 lg:col-span-4">
            <AssistantsCard
              assistants={data.assistants}
              loading={loading}
              error={error}
            />
            <RecentLogsCard logs={data.logs} loading={loading} />
          </div>

          <div className="col-span-1 space-y-4 lg:col-span-3">
            <PluginsCard plugins={data.plugins} loading={loading} />
            <LlmCard llm={data.llm} loading={loading} />
            <MarketCard market={data.market} loading={loading} />
          </div>
        </div>
      </TabsContent>
      <TabsContent value="analytics" className="space-y-4">
        <AnalyticsTab />
      </TabsContent>
    </Tabs>
  );
}
