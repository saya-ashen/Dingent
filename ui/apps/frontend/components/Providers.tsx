"use client";

import { useMemo } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { useAuthStore } from "@repo/store";
import { useAuthInterceptor } from "@repo/store"; // Import the new hook
import { ThreadProvider, useThreadContext } from "@/contexts/ThreadProvider";

// A small inner component to connect CopilotKit with the ThreadProvider state
function CopilotKitWrapper({ children }: { children: React.ReactNode }) {
  const { activeThreadId } = useThreadContext();
  const accessToken = useAuthStore((state) => state.accessToken);

  const headers = useMemo(() => ({
    Authorization: `Bearer ${accessToken || 'None'}`,
  }), [accessToken]);

  // Call the interceptor hook here to activate it
  useAuthInterceptor();

  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
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
