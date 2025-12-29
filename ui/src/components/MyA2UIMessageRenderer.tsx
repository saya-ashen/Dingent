import { type ReactActivityMessageRenderer } from "@copilotkitnext/react";
import { z } from "zod";
import { useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react"; // Shadcn 常用图标库
import { Button } from "@/components/ui/button";
import { DataTable } from "./A2UI/data-table"; // 引入上面写的组件

export type MessageRendererOptions = {
  theme?: any;
};

export function createA2UIMessageRenderer(
  options: MessageRendererOptions,
): ReactActivityMessageRenderer<any> {
  return {
    activityType: "a2ui-surface",

    content: z.any() as any,

    render: ({ content }) => {
      const { columns: rawColumns, rows, title } = content;

      // --- 核心逻辑：动态生成 Shadcn (TanStack) 需要的列定义 ---
      const columns = useMemo<ColumnDef<any>[]>(() => {
        if (!rawColumns) return [];

        return rawColumns.map((colName) => ({
          accessorKey: colName, // 告诉 Table 数据里的 key 是什么 (例如 "Temperature")

          // 自定义表头，增加点击排序功能
          header: ({ column }) => {
            return (
              <Button
                variant="ghost"
                onClick={() =>
                  column.toggleSorting(column.getIsSorted() === "asc")
                }
                className="-ml-3 h-8" // 稍微调整样式使其对齐
              >
                {colName}
                <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            );
          },

          // 单元格渲染
          cell: ({ row }) => {
            const value = row.getValue(colName);
            return <div className="font-medium">{String(value ?? "-")}</div>;
          },
        }));
      }, [rawColumns]);

      if (!rawColumns || rawColumns.length === 0) {
        return <div className="p-4 text-gray-500 italic">No data columns.</div>;
      }

      return (
        <div className="w-full my-4">
          <h3 className="mb-2 text-lg font-semibold tracking-tight">{title}</h3>
          {/* 调用封装好的 DataTable */}
          <DataTable columns={columns} data={rows} />
        </div>
      );
    },
  };
}
