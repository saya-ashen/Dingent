"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import {
  ThemeProvider,
  FontProvider,
  DirectionProvider,
} from "@repo/ui/providers";
import { createQueryClient } from "@repo/lib/query-client";

export function Providers({ children }: { children: React.ReactNode }) {
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
