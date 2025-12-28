import { type ReactActivityMessageRenderer } from "@copilotkitnext/react";
import React, { useMemo } from "react";
import { z } from "zod";

export type A2UIMessageRendererOptions = {
  theme?: any;
};

// 定义解析后的数据结构
type ParsedData = {
  meta: {
    surfaceId?: string;
    root?: string;
    styles?: any;
  };
  components: Array<{
    id: string;
    type: string;
    props: any;
    weight?: number;
  }>;
  dataModel: Array<{
    key: string;
    typeLabel: string;
    value: string;
    path?: string;
  }>;
};

export function createA2UIMessageRenderer(
  options: A2UIMessageRendererOptions,
): ReactActivityMessageRenderer<any> {
  return {
    activityType: "a2ui-surface",
    content: z.any(),
    render: ({ content }) => {
      const operations = content?.operations;

      // 1. 数据解析逻辑：使用 useMemo 避免每次渲染都重新计算
      const parsedData: ParsedData = useMemo(() => {
        const result: ParsedData = {
          meta: {},
          components: [],
          dataModel: [],
        };

        if (!Array.isArray(operations)) return result;

        for (const op of operations) {
          // --- 解析 BeginRendering (元数据) ---
          if (op.beginRendering) {
            result.meta.surfaceId = op.beginRendering.surfaceId;
            result.meta.root = op.beginRendering.root;
            result.meta.styles = op.beginRendering.styles;
          }

          // --- 解析 SurfaceUpdate (组件列表) ---
          if (op.surfaceUpdate && Array.isArray(op.surfaceUpdate.components)) {
            // 如果 meta 还没记录 surfaceId，尝试从这里获取
            if (!result.meta.surfaceId)
              result.meta.surfaceId = op.surfaceUpdate.surfaceId;

            op.surfaceUpdate.components.forEach((c: any) => {
              // c.component 是一个对象，key 是类型名 (如 { Button: {...} })
              const keys = c.component ? Object.keys(c.component) : [];
              const type = keys.length > 0 ? keys[0] : "Unknown";
              const props = keys.length > 0 ? c.component[type] : {};

              result.components.push({
                id: c.id,
                type: type,
                weight: c.weight,
                props: props,
              });
            });
          }

          // --- 解析 DataModelUpdate (数据变量) ---
          if (
            op.dataModelUpdate &&
            Array.isArray(op.dataModelUpdate.contents)
          ) {
            // 如果 meta 还没记录 surfaceId，尝试从这里获取
            if (!result.meta.surfaceId)
              result.meta.surfaceId = op.dataModelUpdate.surfaceId;

            op.dataModelUpdate.contents.forEach((item: any) => {
              const { value, typeLabel } = extractDataValue(item);
              result.dataModel.push({
                key: item.key,
                typeLabel,
                value,
                path: op.dataModelUpdate.path || "/",
              });
            });
          }
        }
        return result;
      }, [operations]);

      if (!operations) {
        return (
          <div className="p-4 text-gray-400 italic">No operations data.</div>
        );
      }

      return (
        <div className="flex flex-col gap-6 w-full my-4">
          {/* 1. Meta Info Section */}
          <MetaInfoCard meta={parsedData.meta} />

          {/* 2. Components Table */}
          {parsedData.components.length > 0 && (
            <TableSection
              title="UI Components Definition"
              count={parsedData.components.length}
              color="blue"
            >
              <thead className="bg-gray-50 text-xs uppercase text-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left">ID</th>
                  <th className="px-6 py-3 text-left">Type</th>
                  <th className="px-6 py-3 text-left">
                    Properties & Attributes
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {parsedData.components.map((comp, idx) => (
                  <tr key={`${comp.id}-${idx}`} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 font-mono">
                      {comp.id}
                    </td>
                    <td className="px-6 py-4 text-sm text-blue-600 font-semibold">
                      {comp.type}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-600 font-mono">
                      {comp.weight !== undefined && (
                        <div className="mb-1">
                          <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
                            Weight: {comp.weight}
                          </span>
                        </div>
                      )}
                      <div className="max-h-32 overflow-y-auto whitespace-pre-wrap break-all">
                        {JSON.stringify(comp.props, null, 1).replace(
                          /[{}\n"]/g,
                          " ",
                        )}
                        {/* 简单的清洗一下 JSON 字符串，或者直接用 pre 显示完整结构 */}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSection>
          )}

          {/* 3. Data Model Table */}
          {parsedData.dataModel.length > 0 && (
            <TableSection
              title="Data Model State"
              count={parsedData.dataModel.length}
              color="green"
            >
              <thead className="bg-gray-50 text-xs uppercase text-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left w-1/4">Key</th>
                  <th className="px-6 py-3 text-left w-1/6">Type</th>
                  <th className="px-6 py-3 text-left">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {parsedData.dataModel.map((data, idx) => (
                  <tr key={`${data.key}-${idx}`} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 font-mono">
                      {data.key}
                    </td>
                    <td className="px-6 py-4 text-xs uppercase text-gray-500">
                      {data.typeLabel}
                    </td>
                    <td className="px-6 py-4 text-sm font-mono text-gray-700 break-all">
                      {data.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSection>
          )}
        </div>
      );
    },
  };
}

// --- 辅助函数：提取 DataModel 的值 ---
function extractDataValue(item: any): { value: string; typeLabel: string } {
  if (item.valueString !== undefined)
    return { value: item.valueString, typeLabel: "String" };
  if (item.valueNumber !== undefined)
    return { value: String(item.valueNumber), typeLabel: "Number" };
  if (item.valueBoolean !== undefined)
    return {
      value: item.valueBoolean ? "TRUE" : "FALSE",
      typeLabel: "Boolean",
    };
  // 针对 valueMap (表格数据)，我们简单地序列化它，避免表格嵌套表格过于混乱
  if (item.valueMap !== undefined)
    return { value: JSON.stringify(item.valueMap), typeLabel: "Map (Complex)" };
  return { value: "null", typeLabel: "Null" };
}

// --- 辅助组件：信息卡片 ---
function MetaInfoCard({ meta }: { meta: ParsedData["meta"] }) {
  if (!meta.surfaceId && !meta.root) return null;
  return (
    <div className="bg-white p-4 rounded-lg border border-purple-100 shadow-sm flex flex-col sm:flex-row gap-4 sm:items-center justify-between">
      <div>
        <span className="text-xs font-bold text-purple-600 uppercase tracking-wide block mb-1">
          Surface Context
        </span>
        <div className="text-sm font-mono text-gray-800">
          ID:{" "}
          <span className="bg-gray-100 px-1 rounded">
            {meta.surfaceId || "N/A"}
          </span>
        </div>
      </div>
      {meta.root && (
        <div className="text-right">
          <span className="text-xs text-gray-400 block mb-1">
            Root Component
          </span>
          <span className="text-sm font-medium bg-purple-50 text-purple-700 px-2 py-1 rounded border border-purple-100">
            {meta.root}
          </span>
        </div>
      )}
    </div>
  );
}

// --- 辅助组件：通用表格容器 ---
function TableSection({ title, count, color, children }: any) {
  const colorStyles: any = {
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    green: "bg-green-50 text-green-700 border-green-200",
  };
  const badgeStyle = colorStyles[color] || colorStyles.blue;

  return (
    <div className="w-full overflow-hidden rounded-lg border border-gray-200 shadow-sm bg-white">
      <div className="px-6 py-3 border-b border-gray-100 flex items-center justify-between bg-white">
        <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        <span
          className={`text-xs font-medium px-2.5 py-0.5 rounded border ${badgeStyle}`}
        >
          Count: {count}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">{children}</table>
      </div>
    </div>
  );
}
