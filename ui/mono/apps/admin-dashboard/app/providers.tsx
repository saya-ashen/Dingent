"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./context/theme-provider";
import { FontProvider } from "./context/font-provider";
import { DirectionProvider } from "./context/direction-provider";

// 导入你的 QueryClient 配置
import { createQueryClient } from "./lib/query-client";

export function Providers({ children }: { children: React.ReactNode }) {
  // 确保 QueryClient 在组件的生命周期内只被创建一次
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <FontProvider>
          <DirectionProvider>
            {children}
            {/* 你可以在这里放置 toast provider, e.g., <Toaster /> from sonner */}
          </DirectionProvider>
        </FontProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
