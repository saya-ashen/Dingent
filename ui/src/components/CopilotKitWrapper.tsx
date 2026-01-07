"use client";

import { useEffect, useMemo, useState } from "react";

import { CopilotKitProvider } from "@copilotkit/react-core/v2";
import { useAuthStore } from "@/store";
import { createA2UIMessageRenderer } from "./MyA2UIMessageRenderer";
import { theme } from "./theme";

export const dynamic = "force-dynamic";

import { useParams } from "next/navigation";
function getOrSetVisitorId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem("dingent_visitor_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("dingent_visitor_id", id);
  }
  return id;
}

function CopilotKitContent({
  children,
  slug,
  accessToken,
}: {
  children: React.ReactNode;
  slug: string;
  accessToken: string | null;
}) {
  const A2UIMessageRenderer = createA2UIMessageRenderer({ theme });
  const activityRenderers = [A2UIMessageRenderer];
  const [visitorId, setVisitorId] = useState<string>("");
  useEffect(() => {
    setVisitorId(getOrSetVisitorId());
  }, []);
  const isGuest = !accessToken;
  const runtimeUrl = isGuest
    ? `/api/v1/${slug}/chat/guest`
    : `/api/v1/${slug}/chat`;
  const headers = useMemo(() => {
    if (isGuest) {
      // 游客模式：只传 X-Visitor-ID
      return {
        "X-Visitor-ID": visitorId,
        WorkspaceSlug: slug,
      };
    } else {
      // 用户模式：传 Authorization
      return {
        Authorization: `Bearer ${accessToken}`,
        WorkspaceSlug: slug,
      };
    }
  }, [isGuest, accessToken, visitorId, slug]);
  if (isGuest && !visitorId) return null;

  return (
    <CopilotKitProvider
      renderActivityMessages={activityRenderers}
      runtimeUrl={runtimeUrl}
      headers={headers}
      properties={{
        authorization: accessToken,
        workspace_slug: slug,
        is_guest: isGuest,
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

  // const headers = useMemo(
  //   () => ({
  //     Authorization: `Bearer ${accessToken || "None"}`,
  //     WorkspaceSlug: slug,
  //   }),
  //   [accessToken, slug],
  // );

  if (!isMounted) {
    return null;
  }

  return (
    <CopilotKitContent slug={slug} accessToken={accessToken}>
      {children}
    </CopilotKitContent>
  );
}
