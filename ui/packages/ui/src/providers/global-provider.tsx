"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./theme-provider";
import { FontProvider } from "./font-provider";
import { DirectionProvider } from "./direction-provider";
import { createQueryClient } from "@repo/lib/query-client";
import { Toaster } from "sonner";

export function GlobalProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <FontProvider>
          <DirectionProvider>
            {children}
            <Toaster richColors position="top-right" />
          </DirectionProvider>
        </FontProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
