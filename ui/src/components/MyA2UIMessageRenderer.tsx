import { type ReactActivityMessageRenderer } from "@copilotkitnext/react";
import { z } from "zod";
import { useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";
import {
  AlertCircle,
  ArrowUpDown,
  Ban,
  CheckCircle2,
  Circle,
  Loader2,
  ListTodo,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "./A2UI/data-table";
import { ErrorBoundary } from "react-error-boundary";

// --- 1. 类型定义 ---

interface TableContent {
  type: "table";
  title?: string;
  columns: string[];
  rows: Record<string, any>[];
}

// 联合类型
type A2UIContent = TableContent;

// --- 2. 错误处理组件 (保持不变) ---

function ErrorFallback({
  error,
  resetErrorBoundary,
}: {
  error: Error;
  resetErrorBoundary: () => void;
}) {
  return (
    <div className="p-4 border border-red-200 bg-red-50 rounded-md text-red-600 flex flex-col gap-2 my-2">
      <div className="flex items-center gap-2 font-semibold">
        <Ban className="w-4 h-4" />
        <span>Component Render Error</span>
      </div>
      <p className="text-sm opacity-80 break-all">{error.message}</p>
      <Button
        variant="outline"
        size="sm"
        onClick={resetErrorBoundary}
        className="w-fit mt-2 bg-white"
      >
        Retry
      </Button>
    </div>
  );
}

function TableView({ data }: { data: TableContent }) {
  const { columns: rawColumns, rows, title } = data;

  // useMemo 必须在组件内部调用，不能在主 render 函数的 if 语句中调用
  const safeColumns = useMemo<ColumnDef<any>[]>(() => {
    try {
      if (!rawColumns || !Array.isArray(rawColumns)) return [];

      return rawColumns.map((colName) => ({
        accessorKey: colName,
        header: ({ column }) => (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="-ml-3 h-8"
          >
            {colName}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        ),
        cell: ({ row }) => {
          try {
            const value = row.getValue(colName);
            return <div className="font-medium">{String(value ?? "-")}</div>;
          } catch (e) {
            return <span className="text-red-400 text-xs">Error</span>;
          }
        },
      }));
    } catch (e) {
      console.error("Error generating columns:", e);
      return [];
    }
  }, [rawColumns]);

  if (!rawColumns || rawColumns.length === 0) {
    return (
      <div className="p-4 text-gray-500 italic">No data columns available.</div>
    );
  }

  return (
    <div className="w-full my-4 space-y-2">
      {title && (
        <h3 className="text-lg font-semibold tracking-tight px-1">{title}</h3>
      )}
      {safeColumns.length > 0 ? (
        <DataTable columns={safeColumns} data={rows || []} />
      ) : (
        <div className="text-sm text-red-500">
          Could not render table columns.
        </div>
      )}
    </div>
  );
}

// --- 5. 主渲染器工厂函数 ---

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
      // 1. 基础空值检查
      if (!content || typeof content !== "object") {
        return (
          <div className="p-4 border border-red-200 rounded text-red-500 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>Data format error: Content is missing or invalid.</span>
          </div>
        );
      }

      // 2. 根据 type 分发渲染逻辑
      // 使用 ErrorBoundary 包裹整个动态内容，确保任意组件崩溃不影响聊天主界面
      return (
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          {(() => {
            const typedContent = content as A2UIContent;

            switch (typedContent.type) {
              case "table":
                return <TableView data={typedContent} />;

              default:
                if ("rows" in content && "columns" in content) {
                  return <TableView data={{ ...content, type: "table" }} />;
                }

                return (
                  <div className="p-4 border border-yellow-200 bg-yellow-50 rounded text-yellow-700 text-sm">
                    <p className="font-semibold">
                      Unknown content type: {content.type}
                    </p>
                    <pre className="mt-2 text-xs opacity-80 overflow-auto max-h-40">
                      {JSON.stringify(content, null, 2)}
                    </pre>
                  </div>
                );
            }
          })()}
        </ErrorBoundary>
      );
    },
  };
}
