import { useOverview } from "./useOverview";
import { Button } from "@repo/ui/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@repo/ui/components/ui/tabs";
import { ConfigDrawer } from "@repo/ui/components/config-drawer";
import { FloatingActionButtons } from "@repo/ui/components/layout/floating-action-button";
import { Header } from "@repo/ui/components/layout/header";
import { Main } from "@repo/ui/components/layout/main";
import { ProfileDropdown } from "@repo/ui/components/profile-dropdown";
import { Search } from "@repo/ui/components/search";
import { ThemeSwitch } from "@repo/ui/components/theme-switch";

import { AnalyticsTab } from "@repo/ui/dashboard/components/analytics-tab";
import { AssistantsCard } from "@repo/ui/dashboard/assistants-card";
import { DashboardStats } from "@repo/ui/dashboard/dashboard-stats";
import { LlmCard } from "@repo/ui/dashboard//llm-card";
import { MarketCard } from "@repo/ui/dashboard/market-card";
import { PluginsCard } from "@repo/ui/dashboard/plugins-card";
import { RecentLogsCard } from "@repo/ui/dashboard/recent-logs-card";

export function Dashboard() {
  const { data, loading, error, reload } = useOverview();

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
        <Tabs
          orientation="vertical"
          defaultValue="overview"
          className="space-y-4"
        >
          <div className="w-full overflow-x-auto pb-2">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
              <TabsTrigger value="reports" disabled>
                Reports
              </TabsTrigger>
              <TabsTrigger value="notifications" disabled>
                Notifications
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="overview" className="space-y-4">
            <DashboardStats stats={data} loading={loading} error={!!error} />

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-7">
              <div className="col-span-1 space-y-4 lg:col-span-4">
                <AssistantsCard
                  assistants={data?.assistants}
                  loading={loading}
                  error={error}
                />
                <RecentLogsCard logs={data?.logs} loading={loading} />
              </div>

              <div className="col-span-1 space-y-4 lg:col-span-3">
                <PluginsCard plugins={data?.plugins} loading={loading} />
                <LlmCard llm={data?.llm} loading={loading} />
                <MarketCard market={data?.market} loading={loading} />
              </div>
            </div>
          </TabsContent>
          <TabsContent value="analytics" className="space-y-4">
            <AnalyticsTab />
          </TabsContent>
        </Tabs>
      </Main>
    </>
  );
}
