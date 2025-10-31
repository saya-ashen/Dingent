"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import {
  ThemeProvider,
  FontProvider,
  DirectionProvider,
} from "@repo/ui/providers";
import { createQueryClient } from "@repo/lib/query-client";
import { setAuthHooks } from "@repo/api-client";
import { useAuthStore } from "@repo/store";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());
  console.log("Setting auth hooks in Providers");
  setAuthHooks({
    getAccessToken: () => useAuthStore.getState().accessToken,
    resetAuthState: () => useAuthStore.getState().reset(),
  });


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
