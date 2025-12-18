"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CopilotKitCSSProperties } from "@copilotkit/react-ui";
import { useAgent, CopilotChat } from "@copilotkit/react-core/v2";

import { getClientApi } from "@/lib/api/client";
import { useActiveWorkflow } from "@repo/store";
import { useThreadContext } from "@/providers/ThreadProvider";
import { ChatHeader } from "@/components/chat-header"; // 假设你放在了这里

export default function CopilotKitPage() {
  const [themeColor] = useState("#6366f1"); // Indigo-500
  const params = useParams();
  const slug = params.slug as string;

  const api = getClientApi().forWorkspace(slug);
  const { workflow } = useActiveWorkflow(api.workflows, slug);

  const { activeThreadId, updateThreadTitle } = useThreadContext();

  // 安全地处理 agent hook，防止 workflow 未加载时报错
  const agentName = workflow?.name || "default";
  const agent = useAgent({ agentId: agentName });
  const isAgentRunning = agent.agent.isRunning;

  useEffect(() => {
    if (activeThreadId) {
      updateThreadTitle(activeThreadId);
    }
  }, [isAgentRunning, activeThreadId, updateThreadTitle]);

  if (!activeThreadId) return null; // 或者返回一个 Loading Skeleton

  return (
    <main
      className="
    flex flex-col h-screen w-full overflow-hidden 
    text-zinc-200
    bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900 via-zinc-950 to-black"
    >
      <ChatHeader className="flex-shrink-0" />

      <CopilotChat
        agentId={workflow?.name}
        threadId={activeThreadId}
        className="h-full w-full relative flex-1 min-h-0 w-full max-w-7xl mx-auto border-x border-neutral-800/30 shadow-2xl shadow-black"
      />
    </main>
  );
}
