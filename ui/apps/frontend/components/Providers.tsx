"use client";

import { useMemo } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { setAuthHooks } from "@repo/api-client";
import { useAuthInterceptor, useActiveWorkflow, useAuthStore } from "@repo/store";
import { ThreadProvider, useThreadContext } from "../contexts/ThreadProvider";


function CopilotKitWrapper({ children }: { children: React.ReactNode }) {
  useAuthInterceptor()
  setAuthHooks({
    getAccessToken: () => useAuthStore.getState().accessToken,
    resetAuthState: () => useAuthStore.getState().reset(),
  });

  const { activeThreadId } = useThreadContext();
  const accessToken = useAuthStore((state) => state.accessToken);
  const { name: workflow_name } = useActiveWorkflow();


  const headers = useMemo(() => ({
    Authorization: `Bearer ${accessToken || 'None'}`,
  }), [accessToken]);

  return (
    <CopilotKit
      runtimeUrl="/api/v1/frontend/copilotkit"
      showDevConsole={false}
      agent={workflow_name}
      threadId={activeThreadId}
      headers={headers}
      properties={{
        authorization: accessToken,
      }}
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
