"use client";

import { ChatThread, Widget, TablePayload, MarkdownPayload } from "@repo/types";
import { MarkdownWidget } from "@repo/ui/components";
import { TableWidget } from "@repo/ui/components";
import { useMemo, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { ThreadContext, useThreadManager } from "@/contexts/ThreadProvider";
import { useAuthStore } from "@repo/store";


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
    // Only add the Authorization header if the token exists
    if (accessToken) {
      return {
        Authorization: `Bearer ${accessToken}`,
      };
    }
    return { Authorization: `Bearer None`, };
  }, [accessToken]);

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
