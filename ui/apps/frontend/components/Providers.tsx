"use client";

import { useMemo } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { useAuthStore } from "@repo/store";
import { useAuthInterceptor } from "@repo/store";
import { ThreadProvider, useThreadContext } from "@/contexts/ThreadProvider";

function CopilotKitWrapper({ children }: { children: React.ReactNode }) {
  useAuthInterceptor()
  const { activeThreadId } = useThreadContext();
  const accessToken = useAuthStore((state) => state.accessToken);

  const headers = useMemo(() => ({
    Authorization: `Bearer ${accessToken || 'None'}`,
  }), [accessToken]);

  return (
    <CopilotKit
      runtimeUrl="/api/v1/frontend/copilotkit"
      showDevConsole={false}
      agent="dingent"
      threadId={activeThreadId}
      headers={headers}
    >
      {children}
    </CopilotKit>
  );
}

// Your main export
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    // The main ThreadProvider now wraps everything
    <ThreadProvider>
      <CopilotKitWrapper>
        {children}
      </CopilotKitWrapper>
    </ThreadProvider>
  );
}
