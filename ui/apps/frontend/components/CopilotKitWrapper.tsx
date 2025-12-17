"use client";

import { useEffect, useMemo, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotKitProvider } from "@copilotkit/react-core/v2"
import { useAuthInterceptor, useAuthStore } from "@repo/store";
import { ThreadProvider, useThreadContext } from "../providers/ThreadProvider";

import { useParams } from "next/navigation";

function CopilotKitContent({ children, headers, slug, accessToken }: {
  children: React.ReactNode,
  headers: any,
  slug: string,
  accessToken: string | null
}) {
  const { activeThreadId } = useThreadContext();


  return (
    <CopilotKitProvider
      runtimeUrl={`/api/v1/${slug}/chat`}
      headers={headers}
      properties={{
        authorization: accessToken,
        workspace_slug: slug,
      }}
    >
      {children}
    </CopilotKitProvider>
  );
}

export function CopilotKitWrapper({ children }: { children: React.ReactNode }) {
  // useAuthInterceptor();

  const accessToken = useAuthStore((state) => state.accessToken);
  const params = useParams();
  const slug = params.slug as string;
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // 修复依赖项：添加 slug
  const headers = useMemo(() => ({
    Authorization: `Bearer ${accessToken || "None"}`,
    WorkspaceSlug: slug,
  }), [accessToken, slug]);

  if (!isMounted) {
    return null;
  }

  return (
    <ThreadProvider>
      <CopilotKitContent headers={headers} slug={slug} accessToken={accessToken}>
        {children}
      </CopilotKitContent>
    </ThreadProvider>
  );
}
