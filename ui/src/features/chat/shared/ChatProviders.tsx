'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, ReactNode } from 'react';
import { cn } from "@/lib/utils";
import { LayoutProvider, SearchProvider } from "@/providers/";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ThreadProvider } from "@/providers/ThreadProvider";

interface ChatProvidersProps {
  children: ReactNode;
  sidebar?: ReactNode;
  visitorId?: string;
  className?: string;
}

export default function ChatProviders({
  children,
  sidebar,
  visitorId,
  className
}: ChatProvidersProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        // Guest mode retry strategy
        retry: (failureCount, error: any) => {
          if (error?.status === 403 || error?.status === 401) return false;
          return failureCount < 3;
        },
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <SearchProvider>
        <ThreadProvider visitorId={visitorId}>
          <LayoutProvider>
            <SidebarProvider className={cn("h-svh overflow-hidden", className)}>
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
