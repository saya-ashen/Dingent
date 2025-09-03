import { useEffect, useState, useMemo } from 'react'
import { getOverview } from '@/lib/api'
import type { OverviewData } from '@/lib/types'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfigDrawer } from '@/components/config-drawer'
import { FloatingActionButtons } from '@/components/layout/floating-action-button'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { AnalyticsTab } from './components/analytics-tab'
import { AssistantsTable } from './components/assistants-table'
import { LLMInfo } from './components/llm-info'
import { PluginsMiniList } from './components/plugins-minilist'
import { RecentLogs } from './components/recent-logs'
import { StatCard } from './components/stat-card'

function useOverview() {
  const [data, setData] = useState<OverviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = () => {
    setLoading(true)
    setError(null)
    getOverview()
      .then((d) => {
        setData(d)
      })
      .catch((e: Error) => {
        setError(e.message)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
  }, [])

  return { data, loading, error, reload }
}
export function Dashboard() {
  const { data, loading, error, reload } = useOverview()

  const assistants = data?.assistants
  const plugins = data?.plugins
  const workflows = data?.workflows
  const logs = data?.logs
  const market = data?.market
  const llm = data?.llm

  const assistantActivationRate = useMemo(() => {
    if (!assistants) return ''
    if (!assistants.total) return '0%'
    return (
      ((assistants.active / assistants.total) * 100).toFixed(0) + '% active'
    )
  }, [assistants])

  return (
    <>
      <Header>
        <div className='ms-auto flex items-center space-x-4'>
          <Search />
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>
      <FloatingActionButtons>
        <Button variant='outline' onClick={reload} disabled={loading}>
          Refresh
        </Button>
      </FloatingActionButtons>
      <Main>
        <div className='mb-2 flex items-center justify-between space-y-2'>
          <h1 className='text-2xl font-bold tracking-tight'>Dashboard</h1>
          <div className='flex items-center space-x-2'></div>
        </div>
        <Tabs
          orientation='vertical'
          defaultValue='overview'
          className='space-y-4'
        >
          <div className='w-full overflow-x-auto pb-2'>
            <TabsList>
              <TabsTrigger value='overview'>Overview</TabsTrigger>
              <TabsTrigger value='analytics'>Analytics</TabsTrigger>
              <TabsTrigger value='reports' disabled>
                Reports
              </TabsTrigger>
              <TabsTrigger value='notifications' disabled>
                Notifications
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value='overview' className='space-y-4'>
            <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
              <StatCard
                title='Assistants'
                value={assistants ? assistants.total : '--'}
                sub={assistantActivationRate}
                loading={loading}
                error={!!error}
              />
              <StatCard
                title='Active Assistants'
                value={assistants ? assistants.active : '--'}
                sub={assistants ? `${assistants.inactive} inactive` : ''}
                loading={loading}
                error={!!error}
              />
              <StatCard
                title='Plugins'
                value={plugins ? plugins.installed_total : '--'}
                sub={
                  market
                    ? market.plugin_updates > 0
                      ? `${market.plugin_updates} updates available`
                      : 'Up to date'
                    : ''
                }
                loading={loading}
                error={!!error}
              />
              <StatCard
                title='Workflows'
                value={workflows ? workflows.total : '--'}
                sub={
                  workflows?.active_workflow_id
                    ? `Active: ${workflows.active_workflow_id}`
                    : 'No active workflow'
                }
                loading={loading}
                error={!!error}
              />
            </div>

            <div className='grid grid-cols-1 gap-4 lg:grid-cols-7'>
              <div className='col-span-1 space-y-4 lg:col-span-4'>
                <Card>
                  <CardHeader>
                    <CardTitle>Assistants</CardTitle>
                    <CardDescription>
                      {assistants
                        ? `Total ${assistants.total}, Active ${assistants.active}, Inactive ${assistants.inactive}`
                        : 'Overview of assistants'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {error && (
                      <div className='text-destructive mb-2 text-sm'>
                        Failed to load: {error}
                      </div>
                    )}
                    <AssistantsTable
                      items={assistants?.list || []}
                      loading={loading}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Recent Logs</CardTitle>
                    <CardDescription>
                      {logs?.stats?.total
                        ? `Total logs: ${logs.stats.total}`
                        : 'Latest captured runtime logs'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <RecentLogs
                      logs={logs?.recent || []}
                      loading={loading}
                      limit={8}
                    />
                  </CardContent>
                </Card>
              </div>

              <div className='col-span-1 space-y-4 lg:col-span-3'>
                <Card>
                  <CardHeader>
                    <CardTitle>Plugins</CardTitle>
                    <CardDescription>
                      {plugins
                        ? `${plugins.installed_total} installed`
                        : 'Installed plugins'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <PluginsMiniList
                      plugins={plugins?.list || []}
                      loading={loading}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>LLM Configuration</CardTitle>
                    <CardDescription>
                      Overview of the current global model configuration
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <LLMInfo llm={llm || {}} loading={loading} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Market</CardTitle>
                    <CardDescription>
                      {market?.metadata?.version
                        ? `Version: ${market.metadata.version}`
                        : 'Marketplace metadata'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className='space-y-2 text-sm'>
                    {loading ? (
                      <Skeleton className='h-5 w-40' />
                    ) : market ? (
                      <>
                        <div>
                          Plugin Updates:{' '}
                          {market.plugin_updates > 0 ? (
                            <span className='font-medium text-amber-600 dark:text-amber-400'>
                              {market.plugin_updates} available
                            </span>
                          ) : (
                            <span className='text-muted-foreground'>
                              No updates
                            </span>
                          )}
                        </div>
                        {market.metadata?.counts && (
                          <div className='text-muted-foreground'>
                            Counts: {JSON.stringify(market.metadata.counts)}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className='text-muted-foreground'>
                        Could not retrieve market data
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>
          <TabsContent value='analytics' className='space-y-4'>
            <AnalyticsTab />
          </TabsContent>
        </Tabs>
      </Main>
    </>
  )
}
