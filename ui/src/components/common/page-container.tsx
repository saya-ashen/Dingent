import React from "react";
import { cn } from "@/lib/utils"; // 假设你有类似 shadcn/ui 的工具，没有可以去掉

interface PageContainerProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  action?: React.ReactNode; // 可选：用于在标题右侧放按钮
  className?: string;       // 可选：用于覆盖最外层样式
}

export function PageContainer({
  title,
  description,
  children,
  action,
  className
}: PageContainerProps) {
  return (
    <div className={cn("flex flex-col h-full w-full p-6", className)}>

      <div className="flex items-start justify-between mb-6 flex-shrink-0">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {description && (
            <p className="text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {children}
      </div>
    </div>
  );
}
