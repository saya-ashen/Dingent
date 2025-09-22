"use client";

import { type ChangeEvent, useState, useCallback } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
  UseMutationResult,
} from "@tanstack/react-query";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { cn, getErrorMessage } from "@repo/lib/utils";
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
} from "lucide-react";
import { toast } from "sonner";

// API and types
import {
  api,
  MarketItem,
  MarketDownloadResponse,
  MarketDownloadRequest,
} from "@repo/api-client";

// UI Components
import {
  Button,
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Input,
  Separator,
  ConfigDrawer,
  EmptyState,
  Header,
  Main,
  LoadingSkeleton,
  ProfileDropdown,
  Search,
  ThemeSwitch,
} from "@repo/ui/components";

// --- Helper Types and Constants ---
type CategoryFilter = "all" | "plugin" | "assistant" | "workflow";

const categoryText = new Map<CategoryFilter, string>([
  ["all", "All"],
  ["plugin", "Plugins"],
  ["assistant", "Assistants"],
  ["workflow", "Workflows"],
]);

// MarketItemActionButton 组件保持不变
function MarketItemActionButton({
  item,
  mutation,
}: {
  item: MarketItem;
  mutation: UseMutationResult<
    MarketDownloadResponse,
    unknown,
    MarketDownloadRequest,
    unknown
  >;
}) {
  const isMutatingThisItem =
    mutation.isPending && mutation.variables?.item_id === item.id;

  const handleAction = () => {
    mutation.mutate({
      item_id: item.id,
      category: item.category,
      isUpdate: item.update_available || false,
    });
  };

  if (item.update_available) {
    return (
      <Button
        onClick={handleAction}
        disabled={isMutatingThisItem}
        className="w-full bg-yellow-500 text-black hover:bg-yellow-600"
      >
        <ArrowUpCircle className="mr-2 h-4 w-4" />
        {isMutatingThisItem ? "Updating..." : "Update"}
      </Button>
    );
  }

  if (item.is_installed) {
    return (
      <Button disabled className="w-full">
        <CheckCircle className="mr-2 h-4 w-4" />
        Installed
      </Button>
    );
  }

  return (
    <Button
      onClick={handleAction}
      disabled={isMutatingThisItem}
      className="w-full"
    >
      <Download className="mr-2 h-4 w-4" />
      {isMutatingThisItem ? "Downloading..." : "Download"}
    </Button>
  );
}

export function MarketPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const initialFilter = searchParams.get("filter") || "";
  const initialType = searchParams.get("type") || "all";
  const initialSort = searchParams.get("sort") || "asc";

  const [sort, setSort] = useState<"asc" | "desc">(
    initialSort === "desc" ? "desc" : "asc",
  );
  const [category, setCategory] = useState<CategoryFilter>(
    (["all", "plugin", "assistant", "workflow"].includes(initialType)
      ? initialType
      : "all") as CategoryFilter,
  );
  const [searchTerm, setSearchTerm] = useState(initialFilter);

  const qc = useQueryClient();

  // React Query 的数据获取逻辑保持不变
  const metadataQuery = useQuery({
    queryKey: ["market-metadata"],
    queryFn: api.dashboard.market.getMetadata,
    staleTime: 300_000,
  });

  const itemsQuery = useQuery({
    queryKey: ["market-items", category],
    queryFn: () => api.dashboard.market.list(category),
    staleTime: 60_000,
  });

  const downloadMutation = useMutation({
    mutationFn: api.dashboard.market.download,
    onSuccess: (_data, variables) => {
      const action = variables.isUpdate ? "updated" : "downloaded";
      toast.success(
        `Successfully ${action} ${variables.category}: ${variables.item_id}`,
      );
      qc.invalidateQueries({ queryKey: ["market-items"] });
      qc.invalidateQueries({ queryKey: ["available-plugins"] });
      qc.invalidateQueries({ queryKey: ["assistants"] });
      qc.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (e: unknown) =>
      toast.error(getErrorMessage(e, "Operation failed")),
  });

  // highlight-start
  // 更改 5: 创建一个可复用的函数来更新 URL 搜索参数
  const updateSearchParams = useCallback(
    (name: string, value: string | undefined) => {
      const current = new URLSearchParams(Array.from(searchParams.entries()));

      if (!value) {
        current.delete(name);
      } else {
        current.set(name, value);
      }

      const search = current.toString();
      const query = search ? `?${search}` : "";
      // 使用 router.push 更新 URL，这不会导致页面重新加载
      router.push(`${pathname}${query}`);
    },
    [searchParams, pathname, router],
  );
  // highlight-end

  // highlight-start
  // 更改 6: 重写事件处理函数
  const handleSearch = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    updateSearchParams("filter", value);
  };

  const handleCategoryChange = (value: CategoryFilter) => {
    setCategory(value);
    updateSearchParams("type", value === "all" ? undefined : value);
  };

  const handleSortChange = (value: "asc" | "desc") => {
    setSort(value);
    updateSearchParams("sort", value);
  };
  // highlight-end

  // 辅助函数和过滤逻辑保持不变
  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "plugin":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
      case "assistant":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
      case "workflow":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300";
    }
  };

  const formatCategory = (cat?: string) =>
    !cat ? "Uncategorized" : cat.charAt(0).toUpperCase() + cat.slice(1);

  const filteredItems = (itemsQuery.data || [])
    .filter((item) =>
      searchTerm
        ? item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.tags?.some((t) =>
          t.toLowerCase().includes(searchTerm.toLowerCase()),
        )
        : true,
    )
    .sort((a, b) =>
      sort === "asc"
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name),
    );

  // JSX 渲染部分完全保持不变
  return (
    <>
      <Header>
        <Search />
        <div className="ms-auto flex items-center gap-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Marketplace Integrations
          </h1>
          <p className="text-muted-foreground">
            Browse plugins, assistants, and workflows from the community
            marketplace.
          </p>
        </div>

        {/* 统计卡片 */}
        {metadataQuery.isLoading && (
          <div className="mt-4">
            <LoadingSkeleton lines={1} />
          </div>
        )}
        {metadataQuery.data && (
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Items
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metadataQuery.data.categories.plugins +
                    metadataQuery.data.categories.assistants +
                    metadataQuery.data.categories.workflows}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Plugins</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metadataQuery.data.categories.plugins}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Assistants
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metadataQuery.data.categories.assistants}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Workflows</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metadataQuery.data.categories.workflows}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 控制栏 */}
        <div className="my-4 flex flex-col justify-between gap-4 sm:my-0 sm:flex-row sm:items-center">
          <div className="flex flex-col gap-4 sm:my-4 sm:flex-row">
            <Input
              placeholder="Search items..."
              className="h-9 w-40 lg:w-[250px]"
              value={searchTerm}
              onChange={handleSearch}
            />
            <Select value={category} onValueChange={handleCategoryChange}>
              <SelectTrigger className="w-40">
                <SelectValue>{categoryText.get(category)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="plugin">Plugins</SelectItem>
                <SelectItem value="assistant">Assistants</SelectItem>
                <SelectItem value="workflow">Workflows</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Select
            value={sort}
            onValueChange={(v: "asc" | "desc") => handleSortChange(v)}
          >
            <SelectTrigger className="w-16">
              <SelectValue>
                <SlidersHorizontal size={18} />
              </SelectValue>
            </SelectTrigger>
            <SelectContent align="end">
              <SelectItem value="asc">
                <div className="flex items-center gap-4">
                  <ArrowUpAZ size={16} />
                  <span>Ascending</span>
                </div>
              </SelectItem>
              <SelectItem value="desc">
                <div className="flex items-center gap-4">
                  <ArrowDownAZ size={16} />
                  <span>Descending</span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Separator className="shadow-sm" />

        {/* 状态显示 */}
        <div className="mt-4">
          {itemsQuery.isLoading && <LoadingSkeleton lines={5} />}
          {itemsQuery.error && (
            <div className="text-red-600">Failed to load market items.</div>
          )}
          {itemsQuery.data && filteredItems.length === 0 && (
            <EmptyState title="No items found" />
          )}
        </div>

        {/* 列表 */}
        <div className="grid gap-4 pt-4 pb-16 sm:grid-cols-2 lg:grid-cols-3">
          {filteredItems.map((item) => (
            <Card key={item.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{item.name}</CardTitle>
                    {item.version && (
                      <Badge
                        variant="outline"
                        className={cn("mt-1", {
                          "border-yellow-500 text-yellow-600":
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
                <CardDescription className="mt-2">
                  {item.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="flex-1">
                {item.tags && item.tags.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-1">
                    {item.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        <Tag className="mr-1 h-3 w-3" />
                        {tag}
                      </Badge>
                    ))}
                    {item.tags.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{item.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
                <div className="text-muted-foreground space-y-2 text-sm">
                  {item.author && (
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span>{item.author}</span>
                    </div>
                  )}
                  {item.rating && (
                    <div className="flex items-center gap-2">
                      <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      <span>{item.rating}/5</span>
                    </div>
                  )}
                  {item.updated_at && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
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
  );
}
