import { type ChangeEvent, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRouteApi } from '@tanstack/react-router'
import {
  SlidersHorizontal,
  ArrowUpAZ,
  ArrowDownAZ,
  Tag,
  Download,
  Star,
  Calendar,
  User,
  ArrowUpCircle,
  CheckCircle,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  getMarketItems,
  getMarketMetadata,
  downloadMarketItem,
} from '@/lib/api'
import type { MarketItem } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { ConfigDrawer } from '@/components/config-drawer'
import { EmptyState } from '@/components/empty-state'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { LoadingSkeleton } from '@/components/loading-skeleton'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'

const route = getRouteApi('/_authenticated/market/')

// 分类类型映射到市场：插件 / 助手 / 工作流
type CategoryFilter = 'all' | 'plugin' | 'assistant' | 'workflow'

const categoryText = new Map<CategoryFilter, string>([
  ['all', 'All'],
  ['plugin', 'Plugins'],
  ['assistant', 'Assistants'],
  ['workflow', 'Workflows'],
])

function MarketItemActionButton({
  item,
  mutation,
}: {
  item: MarketItem
  mutation: any
}) {
  const isMutatingThisItem =
    mutation.isPending && mutation.variables?.item_id === item.id

  const handleAction = () => {
    mutation.mutate({
      item_id: item.id,
      category: item.category,
      isUpdate: item.update_available,
    })
  }

  if (item.update_available) {
    return (
      <Button
        onClick={handleAction}
        disabled={isMutatingThisItem}
        className='w-full bg-yellow-500 text-black hover:bg-yellow-600'
      >
        <ArrowUpCircle className='mr-2 h-4 w-4' />
        {isMutatingThisItem ? 'Updating...' : 'Update'}
      </Button>
    )
  }

  if (item.is_installed) {
    return (
      <Button disabled className='w-full'>
        <CheckCircle className='mr-2 h-4 w-4' />
        Installed
      </Button>
    )
  }

  return (
    <Button
      onClick={handleAction}
      disabled={isMutatingThisItem}
      className='w-full'
    >
      <Download className='mr-2 h-4 w-4' />
      {isMutatingThisItem ? 'Downloading...' : 'Download'}
    </Button>
  )
}

export function Apps() {
  const {
    filter = '',
    type = 'all',
    sort: initSort = 'asc',
  } = route.useSearch() as { filter: string; type: string; sort: string }
  const navigate = route.useNavigate()

  const [sort, setSort] = useState<'asc' | 'desc'>(
    initSort === 'desc' ? 'desc' : 'asc'
  )
  const [category, setCategory] = useState<CategoryFilter>(
    (['all', 'plugin', 'assistant', 'workflow'].includes(type)
      ? type
      : 'all') as CategoryFilter
  )
  const [searchTerm, setSearchTerm] = useState(filter)

  const qc = useQueryClient()

  // 元数据（数量统计）
  const metadataQuery = useQuery({
    queryKey: ['market-metadata'],
    queryFn: getMarketMetadata,
    staleTime: 300_000,
  })

  // 条目数据
  const itemsQuery = useQuery({
    queryKey: ['market-items', category],
    queryFn: () => getMarketItems(category),
    staleTime: 60_000,
  })

  const downloadMutation = useMutation({
    mutationFn: downloadMarketItem,
    onSuccess: (_data, variables) => {
      const action = variables.isUpdate ? 'updated' : 'downloaded'
      toast.success(
        `Successfully ${action} ${variables.category}: ${variables.item_id}`
      )
      qc.invalidateQueries({ queryKey: ['market-items'] })
      qc.invalidateQueries({ queryKey: ['available-plugins'] })
      qc.invalidateQueries({ queryKey: ['assistants'] })
      qc.invalidateQueries({ queryKey: ['workflows'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Operation failed')
    },
  })

  const handleSearch = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchTerm(value)
    navigate({
      search: (prev) => ({
        ...prev,
        filter: value || undefined,
      }),
    })
  }

  const handleCategoryChange = (value: CategoryFilter) => {
    setCategory(value)
    navigate({
      search: (prev) => ({
        ...prev,
        type: value === 'all' ? undefined : value,
      }),
    })
  }

  const handleSortChange = (value: 'asc' | 'desc') => {
    setSort(value)
    navigate({
      search: (prev) => ({
        ...prev,
        sort: value,
      }),
    })
  }

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'plugin':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
      case 'assistant':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      case 'workflow':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
    }
  }

  const formatCategory = (cat?: string) =>
    !cat ? 'Uncategorized' : cat.charAt(0).toUpperCase() + cat.slice(1)

  // 过滤 + 排序
  const filteredItems = (itemsQuery.data || [])
    .filter((item) =>
      searchTerm
        ? item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.tags?.some((t) =>
            t.toLowerCase().includes(searchTerm.toLowerCase())
          )
        : true
    )
    .sort((a, b) =>
      sort === 'asc'
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name)
    )

  return (
    <>
      <Header>
        <Search />
        <div className='ms-auto flex items-center gap-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main fixed>
        <div>
          <h1 className='text-2xl font-bold tracking-tight'>
            Marketplace Integrations
          </h1>
          <p className='text-muted-foreground'>
            Browse plugins, assistants, and workflows from the community
            marketplace.
          </p>
        </div>

        {/* 统计卡片 */}
        {metadataQuery.isLoading && (
          <div className='mt-4'>
            <LoadingSkeleton lines={1} />
          </div>
        )}
        {metadataQuery.data && (
          <div className='mt-4 grid grid-cols-2 gap-4 md:grid-cols-4'>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm font-medium'>
                  Total Items
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='text-2xl font-bold'>
                  {metadataQuery.data.categories.plugins +
                    metadataQuery.data.categories.assistants +
                    metadataQuery.data.categories.workflows}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm font-medium'>Plugins</CardTitle>
              </CardHeader>
              <CardContent>
                <div className='text-2xl font-bold'>
                  {metadataQuery.data.categories.plugins}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm font-medium'>
                  Assistants
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='text-2xl font-bold'>
                  {metadataQuery.data.categories.assistants}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm font-medium'>Workflows</CardTitle>
              </CardHeader>
              <CardContent>
                <div className='text-2xl font-bold'>
                  {metadataQuery.data.categories.workflows}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 控制栏 */}
        <div className='my-4 flex flex-col justify-between gap-4 sm:my-0 sm:flex-row sm:items-center'>
          <div className='flex flex-col gap-4 sm:my-4 sm:flex-row'>
            <Input
              placeholder='Search items...'
              className='h-9 w-40 lg:w-[250px]'
              value={searchTerm}
              onChange={handleSearch}
            />
            <Select value={category} onValueChange={handleCategoryChange}>
              <SelectTrigger className='w-40'>
                <SelectValue>{categoryText.get(category)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='all'>All</SelectItem>
                <SelectItem value='plugin'>Plugins</SelectItem>
                <SelectItem value='assistant'>Assistants</SelectItem>
                <SelectItem value='workflow'>Workflows</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Select value={sort} onValueChange={(v: any) => handleSortChange(v)}>
            <SelectTrigger className='w-16'>
              <SelectValue>
                <SlidersHorizontal size={18} />
              </SelectValue>
            </SelectTrigger>
            <SelectContent align='end'>
              <SelectItem value='asc'>
                <div className='flex items-center gap-4'>
                  <ArrowUpAZ size={16} />
                  <span>Ascending</span>
                </div>
              </SelectItem>
              <SelectItem value='desc'>
                <div className='flex items-center gap-4'>
                  <ArrowDownAZ size={16} />
                  <span>Descending</span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Separator className='shadow-sm' />

        {/* 状态显示 */}
        <div className='mt-4'>
          {itemsQuery.isLoading && <LoadingSkeleton lines={5} />}
          {itemsQuery.error && (
            <div className='text-red-600'>Failed to load market items.</div>
          )}
          {itemsQuery.data && filteredItems.length === 0 && (
            <EmptyState title='No items found' />
          )}
        </div>

        {/* 列表 */}
        <div className='grid gap-4 pt-4 pb-16 sm:grid-cols-2 lg:grid-cols-3'>
          {filteredItems.map((item) => (
            <Card key={item.id} className='flex flex-col'>
              <CardHeader>
                <div className='flex items-start justify-between'>
                  <div className='flex-1'>
                    <CardTitle className='text-lg'>{item.name}</CardTitle>
                    {item.version && (
                      <Badge
                        variant='outline'
                        className={cn('mt-1', {
                          'border-yellow-500 text-yellow-600':
                            item.update_available,
                        })}
                      >
                        {item.update_available
                          ? `v${item.installed_version} → v${item.version}`
                          : `v${item.version}`}
                      </Badge>
                    )}
                  </div>
                  <Badge className={getCategoryColor(item.category)}>
                    {formatCategory(item.category)}
                  </Badge>
                </div>
                <CardDescription className='mt-2'>
                  {item.description}
                </CardDescription>
              </CardHeader>

              <CardContent className='flex-1'>
                {item.tags && item.tags.length > 0 && (
                  <div className='mb-3 flex flex-wrap gap-1'>
                    {item.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant='secondary' className='text-xs'>
                        <Tag className='mr-1 h-3 w-3' />
                        {tag}
                      </Badge>
                    ))}
                    {item.tags.length > 3 && (
                      <Badge variant='secondary' className='text-xs'>
                        +{item.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
                <div className='text-muted-foreground space-y-2 text-sm'>
                  {item.author && (
                    <div className='flex items-center gap-2'>
                      <User className='h-4 w-4' />
                      <span>{item.author}</span>
                    </div>
                  )}
                  {item.rating && (
                    <div className='flex items-center gap-2'>
                      <Star className='h-4 w-4 fill-yellow-400 text-yellow-400' />
                      <span>{item.rating}/5</span>
                    </div>
                  )}
                  {item.updated_at && (
                    <div className='flex items-center gap-2'>
                      <Calendar className='h-4 w-4' />
                      <span>
                        Updated {new Date(item.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>

              <CardFooter>
                <MarketItemActionButton
                  item={item}
                  mutation={downloadMutation}
                />
              </CardFooter>
            </Card>
          ))}
        </div>
      </Main>
    </>
  )
}
