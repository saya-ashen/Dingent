import { SlidersHorizontal, ArrowUpAZ, ArrowDownAZ } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CategoryFilter, SortOption, useMarketFilters } from "../hooks/use-market-filters";

// 使用 Map 维护常量
const CATEGORY_LABELS: Record<CategoryFilter, string> = {
  all: "All",
  plugin: "Plugins",
  assistant: "Assistants",
  workflow: "Workflows",
};

export function MarketToolbar() {
  const { filters, setSearch, setCategory, setSort } = useMarketFilters();

  return (
    <div className="my-4 flex flex-col justify-between gap-4 sm:my-0 sm:flex-row sm:items-center">
      <div className="flex flex-col gap-4 sm:my-4 sm:flex-row">
        <Input
          placeholder="Search items..."
          className="h-9 w-40 lg:w-[250px]"
          // 这里使用 defaultValue 配合 onChange，或者受控组件都可以
          // 如果需要极速响应，保持 value={filters.search} 即可
          value={filters.search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select
          value={filters.category}
          onValueChange={(v) => setCategory(v as CategoryFilter)}
        >
          <SelectTrigger className="w-40">
            <SelectValue>{CATEGORY_LABELS[filters.category]}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Select
        value={filters.sort}
        onValueChange={(v) => setSort(v as SortOption)}
      >
        <SelectTrigger className="w-16">
          <SelectValue>
            <SlidersHorizontal size={18} />
          </SelectValue>
        </SelectTrigger>
        <SelectContent align="end">
          <SelectItem value="asc">
            <div className="flex items-center gap-4">
              <ArrowUpAZ size={16} /> <span>Ascending</span>
            </div>
          </SelectItem>
          <SelectItem value="desc">
            <div className="flex items-center gap-4">
              <ArrowDownAZ size={16} /> <span>Descending</span>
            </div>
          </SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
