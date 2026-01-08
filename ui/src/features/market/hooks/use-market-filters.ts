import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";

export type CategoryFilter = "all" | "plugin" | "assistant" | "workflow";
export type SortOption = "asc" | "desc";

export interface MarketFilters {
  search: string;
  category: CategoryFilter;
  sort: SortOption;
}

export function useMarketFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  // 从 URL 获取当前状态，如果没有则使用默认值
  const filters = {
    search: searchParams.get("filter") || "",
    category: (searchParams.get("type") as CategoryFilter) || "all",
    sort: (searchParams.get("sort") as SortOption) || "asc",
  };

  // 创建一个 helper 来生成新的 query string
  const createQueryString = useCallback(
    (name: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === null || value === "") {
        params.delete(name);
      } else {
        params.set(name, value);
      }
      return params.toString();
    },
    [searchParams],
  );

  const setFilter = (key: string, value: string | null) => {
    // 使用 startTransition 避免 UI 阻塞
    startTransition(() => {
      const queryString = createQueryString(key, value);
      // 使用 replace 而不是 push，避免用户点后退时需要点很多次
      // scroll: false 防止更新过滤条件时页面跳动
      router.replace(`${pathname}?${queryString}`, { scroll: false });
    });
  };

  return {
    filters,
    isPending,
    setSearch: (val: string) => setFilter("filter", val),
    setCategory: (val: CategoryFilter) =>
      setFilter("type", val === "all" ? null : val),
    setSort: (val: SortOption) => setFilter("sort", val),
  };
}
