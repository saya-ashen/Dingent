"use client";

import { useEffect, useMemo, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { useAuthInterceptor, useAuthStore } from "@repo/store";
import { ThreadProvider, useThreadContext } from "../contexts/ThreadProvider";
import { useParams } from "next/navigation";


function CopilotKitWrapper({ children }: { children: React.ReactNode }) {
  useAuthInterceptor()

  const { activeThreadId } = useThreadContext();
  const accessToken = useAuthStore((state) => state.accessToken);
  const params = useParams();
  const slug = params.slug as string;
  // const { name: workflow_name } = useActiveWorkflow();
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);


  const headers = useMemo(() => ({
    Authorization: `Bearer ${accessToken || 'None'}`,
    WorkspaceSlug: slug,
  }), [accessToken]);
  if (!isMounted) {
    return null;
  }

  return (
    <CopilotKit
      runtimeUrl={`/api/v1/${slug}/chat`}
      showDevConsole={false}
      agent={"test"}
      threadId={activeThreadId}
      headers={headers}
      properties={{
        authorization: accessToken,
        workspace_slug: slug
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
