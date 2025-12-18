"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@repo/lib/query-client";
import {
  ThemeProvider,
  FontProvider,
  DirectionProvider,
} from "@repo/ui/providers";

export function Providers({ children }: { children: React.ReactNode }) {
  // 确保 QueryClient 在组件生命周期内只创建一次
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <FontProvider>
          <DirectionProvider>{children}</DirectionProvider>
        </FontProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
