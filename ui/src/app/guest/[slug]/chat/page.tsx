"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAgent, CopilotSidebar } from "@copilotkit/react-core/v2";

import { useWorkspaceApi } from "@/hooks/use-workspace-api";
import { useThreadContext } from "@/providers/ThreadProvider";
import { ChatHeader } from "@/features/chat/chat-header";
import { CopilotChatMessageViewNoActivity } from "@/components/CopilotChatMessageViewNoActivity";
import { CopilotChatActivityList } from "@/components/CopilotChatActivityMessage";
import { useActiveWorkflow } from "@/features/workflows/hooks";

export default function GuestChatPage() {
  const params = useParams();
  const slug = params.slug as string;

  // 1. 获取 visitorId (从 localStorage 或 Context，这里简单起见直接读)
  // 注意：在 Layout 中已经确保了 ID 存在，这里也可以用 Context 传递
  const [visitorId, setVisitorId] = useState<string>("");
  useEffect(() => {
    setVisitorId(localStorage.getItem("dingent_visitor_id") || "");
  }, []);

  // 2. 使用支持游客模式的 API Hook (我们在上一步修改过的)
  // 当 visitorId 存在时，api 实例会自动切换为 "Guest Mode"
  const { api } = useWorkspaceApi({ visitorId });

  // 3. 获取 Workflow (Agent) 信息
  // useActiveWorkflow 需要接受 api 实例作为参数，或者内部使用 useWorkspaceApi
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

  if (!visitorId || !activeThreadId) return null;

  return (
    <main
      className="
    flex flex-col h-full w-full overflow-hidden
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
        // 重要：确保 Sidebar 不会尝试渲染需要 Token 的组件
        labels={{
          initial: `Welcome to ${slug}. You are in guest mode.`,
        }}
      />
    </main>
  );
}
