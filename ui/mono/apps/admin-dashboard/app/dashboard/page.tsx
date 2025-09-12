"use client";

import { useOverview } from "./useOverview";
import {
  ConfigDrawer,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Button,
  FloatingActionButtons,
  Header,
  Main,
  ProfileDropdown,
  Search,
  ThemeSwitch,
} from "@repo/ui/components";

import {
  AnalyticsTab,
  AssistantsCard,
  DashboardStats,
  LlmCard,
  MarketCard,
  PluginsCard,
  RecentLogsCard,
} from "@repo/ui/dashboard";

export default function DashboardPage() {
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
