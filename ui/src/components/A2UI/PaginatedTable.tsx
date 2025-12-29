import { useState } from "react";

export type MessageRendererOptions = {
  theme?: any;
};

// 定义每页显示的行数
const PAGE_SIZE = 7;

// --- 1. 核心组件：带翻页功能的表格 ---
export default function PaginatedTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: any[];
}) {
  const [currentPage, setCurrentPage] = useState(1);

  // 计算总页数
  const totalPages = Math.ceil(rows.length / PAGE_SIZE);

  // 计算当前页需要显示的数据
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const currentRows = rows.slice(startIndex, startIndex + PAGE_SIZE);

  // 翻页处理函数
  const goToNext = () => setCurrentPage((p) => Math.min(p + 1, totalPages));
  const goToPrev = () => setCurrentPage((p) => Math.max(p - 1, 1));

  return (
    <div className="w-full overflow-hidden rounded-lg border border-gray-200 shadow-sm bg-white">
      {/* 标题栏 */}
      <div className="px-6 py-3 border-b border-gray-100 flex items-center justify-between bg-blue-50">
        <h3 className="text-sm font-semibold text-blue-800">Data Table</h3>
        <span className="text-xs font-medium px-2.5 py-0.5 rounded border bg-white text-blue-600 border-blue-200">
          Total: {rows.length}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-gray-50 text-xs uppercase text-gray-700">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className="px-6 py-3 text-left">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {currentRows.length > 0 ? (
              currentRows.map((row, rowIdx) => (
                <tr key={rowIdx} className="hover:bg-gray-50">
                  {columns.map((col, colIdx) => (
                    <td
                      key={`${rowIdx}-${colIdx}`}
                      className="px-6 py-4 text-sm text-gray-700"
                    >
                      {row[col] !== undefined ? String(row[col]) : "-"}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-4 text-center text-gray-400 text-sm"
                >
                  No data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 翻页控制栏 (仅当总页数 > 1 时显示) */}
      {totalPages > 1 && (
        <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Page{" "}
            <span className="font-medium text-gray-900">{currentPage}</span> of{" "}
            <span className="font-medium text-gray-900">{totalPages}</span>
          </span>
          <div className="flex gap-2">
            <button
              onClick={goToPrev}
              disabled={currentPage === 1}
              className="px-3 py-1 text-xs font-medium rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={goToNext}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-xs font-medium rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
