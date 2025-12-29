"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import {
  useAgent,
  CopilotChat,
  CopilotSidebar,
} from "@copilotkit/react-core/v2";

import { getClientApi } from "@/lib/api/client";
import { useThreadContext } from "@/providers/ThreadProvider";
import { ChatHeader } from "@/features/chat/chat-header"; // 假设你放在了这里
import { useActiveWorkflow } from "@/features/workflows/hooks";
import { CopilotChatMessageViewNoActivity } from "@/components/CopilotChatMessageViewNoActivity";
import { CopilotChatActivityList } from "@/components/CopilotChatActivityMessage";

export default function CopilotKitPage() {
  const params = useParams();
  const slug = params.slug as string;

  const api = getClientApi().forWorkspace(slug);
  const { workflow } = useActiveWorkflow(api.workflows, slug);

  const { activeThreadId, updateThreadTitle } = useThreadContext();

  const agentName = workflow?.name || "default";
  const agent = useAgent({ agentId: agentName });
  const isAgentRunning = agent.agent.isRunning;
  const messages = agent.agent.messages;
  const activityMessages = messages.filter((m) => m.role === "activity");

  useEffect(() => {
    if (activeThreadId) {
      updateThreadTitle();
    }
  }, [isAgentRunning, activeThreadId, updateThreadTitle]);

  if (!activeThreadId) return null; // 或者返回一个 Loading Skeleton

  return (
    <main
      className="
    flex flex-col h-screen w-full overflow-hidden
    bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900 via-zinc-950 to-black"
    >
      <div
        className="
        flex-shrink-0 w-full h-full max-w-7xl mx-auto px-4 sm:px-6 py-4
         overflow-y-auto
      "
      >
        <CopilotChatActivityList messages={activityMessages} />
      </div>
      <CopilotSidebar
        agentId={workflow?.name}
        threadId={activeThreadId}
        messageView={CopilotChatMessageViewNoActivity}
        header={ChatHeader as any}
      />
    </main>
  );
}
