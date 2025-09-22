"use client";

import { ChatThread, Widget, TablePayload, MarkdownPayload } from "@repo/types";
import { MarkdownWidget } from "@repo/ui/components";
import { TableWidget } from "@repo/ui/components";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { ThreadContext, useThreadManager } from "@/contexts/ThreadProvider";
import { useAuthStore } from "@repo/store";

const LOGIN_PATH = "/auth/login";
// 只拦截这些接口（把 CopilotKit 的 API 放进来）
const AUTH_GUARDED_ENDPOINTS = ["/api/copilotkit", "/api/v1/frontend/copilotkit"];



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

function AppWithThreads({ children }: { children: React.ReactNode }) {
  const { threads, updateThreadTitle, ...threadManager } = useThreadManager();

  const contextValue = useMemo(
    () => ({
      ...threadManager,
      threads,
      updateThreadTitle,
    }),
    [threadManager, threads, updateThreadTitle],
  );

  return (
    <ThreadContext.Provider value={contextValue}>
      {children}
    </ThreadContext.Provider>
  );
}
const THREAD_LIST_KEY = "chatThreadIdList";
const CURRENT_THREAD_ID_KEY = "currentChatThreadId";

function getInitialThreadId(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const storedList: ChatThread[] = JSON.parse(
    localStorage.getItem(THREAD_LIST_KEY) || "[]",
  );
  const lastActiveId = localStorage.getItem(CURRENT_THREAD_ID_KEY);

  if (lastActiveId && storedList.some((thread) => thread.id === lastActiveId)) {
    return lastActiveId;
  }
  if (storedList.length > 0) {
    return storedList[0]?.id;
  }
  return undefined;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [activeThreadId, setActiveThreadId] = useState<string | undefined>(
    getInitialThreadId,
  );
  const accessToken = useAuthStore((state) => state.auth.accessToken);
  const auth = useAuthStore()

  const initialThreadContextValue = useMemo(
    () => ({
      activeThreadId,
      setActiveThreadId,
      threads: [],
      isLoading: true,
      updateThreadTitle: () => { },
      deleteAllThreads: () => { },
    }),
    [activeThreadId],
  );
  const headers = useMemo(() => {
    if (accessToken) {
      return {
        Authorization: `Bearer ${accessToken}`,
      };
    }
    return { Authorization: `Bearer None`, };
  }, [accessToken]);
  const pathname = usePathname();
  const router = useRouter();
  const redirectingRef = useRef(false);

  useEffect(() => {
    // 登录页不打补丁，避免登录页上的 401 导致循环
    if (pathname.startsWith(LOGIN_PATH)) return;

    const originalFetch = window.fetch;

    function toUrl(input: RequestInfo | URL) {
      if (typeof input === "string") return input;
      if (input instanceof URL) return input.toString();
      return input?.url?.toString?.() ?? "";
    }

    function shouldIntercept(url: string) {
      try {
        // 统一用相对路径做判断
        const u = new URL(url, window.location.origin);
        const path = u.pathname;
        // 仅拦截你关心的接口，避免把静态资源、登录接口、健康检查等也拦了
        return AUTH_GUARDED_ENDPOINTS.some(ep => path.startsWith(ep));
      } catch {
        return false;
      }
    }

    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const res = await originalFetch(input, init);

      if (!redirectingRef.current && res.status === 401) {
        const url = toUrl(input);

        if (shouldIntercept(url)) {
          // 避免多次重定向
          redirectingRef.current = true;

          // 带上回跳地址
          const next = encodeURIComponent(window.location.pathname + window.location.search);
          // 用 router.replace 避免历史栈累积
          router.replace(`${LOGIN_PATH}?next=${next}`);
          // 也可以兜底设置 window.location.href
          // window.location.href = `${LOGIN_PATH}?next=${next}`;

          // 阻止调用方继续处理 401 响应
          throw new Error("Unauthorized");
        }
      }

      return res;
    };

    return () => {
      window.fetch = originalFetch;
      redirectingRef.current = false;
    };
  }, [pathname, router]);

  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      showDevConsole={false}
      agent="dingent"
      threadId={activeThreadId}
      headers={headers}
    >
      <ThreadContext.Provider value={initialThreadContextValue}>
        <AppWithThreads>{children}</AppWithThreads>
      </ThreadContext.Provider>
    </CopilotKit >
  );
}
