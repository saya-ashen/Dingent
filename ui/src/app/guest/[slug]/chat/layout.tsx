// ui/src/app/guest/[slug]/layout.tsx
"use client";

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"; // 1. 引入 React Query
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ThreadProvider } from "@/providers/ThreadProvider";
import { CopilotKitWrapper } from "@/components/CopilotKitWrapper";
import { LayoutProvider, SearchProvider } from "@/providers"; // 2. 引入其他通用 Provider
import { Loader2 } from "lucide-react";

export default function GuestLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { slug: string };
}) {
  // === 状态初始化 ===
  const [visitorId, setVisitorId] = useState<string>("");
  const [mounted, setMounted] = useState(false);

  // 初始化 QueryClient (必须放在组件内部使用 useState，防止 SSR 水合问题)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1分钟缓存
            // 游客模式下可能需要更积极的重试策略，或者遇到 401/403 不重试
            retry: (failureCount, error: any) => {
              if (error?.status === 403 || error?.status === 401) return false;
              return failureCount < 3;
            },
          },
        },
      }),
  );

  // === 游客 ID 逻辑 ===
  useEffect(() => {
    let id = localStorage.getItem("dingent_visitor_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("dingent_visitor_id", id);
    }
    setVisitorId(id);
    setMounted(true);
  }, []);

  if (!mounted || !visitorId) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="animate-spin text-muted-foreground" />
      </div>
    );
  }

  // === Provider 嵌套结构 ===
  // 顺序建议：QueryClient -> Search/Layout -> Thread -> Sidebar -> UI
  return (
    <QueryClientProvider client={queryClient}>
      <SearchProvider>
        <LayoutProvider>
          {/* ThreadProvider 放在这里，确保它内部可以使用 QueryClient */}
          <ThreadProvider visitorId={visitorId}>
            <CopilotKitWrapper>
              <SidebarProvider>
                <AppSidebar isGuest={true} />

                <SidebarInset className="overflow-hidden">
                  {children}
                </SidebarInset>
              </SidebarProvider>
            </CopilotKitWrapper>
          </ThreadProvider>
        </LayoutProvider>
      </SearchProvider>
    </QueryClientProvider>
  );
}
