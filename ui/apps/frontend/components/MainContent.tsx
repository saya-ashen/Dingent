"use client";

import { Widget, TablePayload, MarkdownPayload } from "@repo/types";
import { MarkdownWidget, TableWidget } from "@repo/ui/components";

export function MainContent({ widgets }: { widgets: Widget[] }) {
  return (
    <div
      className="h-screen w-full flex flex-col items-center overflow-y-auto pt-8 pb-8 space-y-6"
      style={{ zIndex: 1 }}
    >
      {widgets.length === 0 ? (
        <div className="flex-grow flex justify-center items-center text-gray-500">
          <p className="text-xl p-6 bg-white/60 rounded-lg shadow-md">
            Agent output will appear here...
          </p>
        </div>
      ) : (
        widgets.map((widget) => {
          switch (widget.type) {
            case "table":
              return (
                <TableWidget
                  key={widget.id}
                  data={widget.payload as TablePayload}
                />
              );
            case "markdown":
              return (
                <MarkdownWidget
                  key={widget.id}
                  data={widget.payload as MarkdownPayload}
                />
              );
            default:
              return null;
          }
        })
      )}
    </div>
  );
}
