'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { cn } from "@/lib/utils";
import { LayoutProvider, SearchProvider } from "@/providers/";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ThreadProvider } from "@/providers/ThreadProvider";

export default function Providers({ children, sidebar }: {
  children: React.ReactNode, sidebar: React.ReactNode;
}) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <SearchProvider>
        <ThreadProvider>
          <LayoutProvider>
            <SidebarProvider className="h-svh overflow-hidden">
              {sidebar}
              <SidebarInset
                id="main-content"
                className={cn(
                  "relative flex flex-col h-full min-h-0 overflow-hidden",
                  "@container/content"
                )}
              >
                {children}
              </SidebarInset>
            </SidebarProvider>
          </LayoutProvider>
        </ThreadProvider>
      </SearchProvider>
    </QueryClientProvider>
  );
}
