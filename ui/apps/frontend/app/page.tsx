"use client";

import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import React, { useState } from "react";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { MainContent } from "@/components/MainContent";
import { useWidgets } from "@/hooks/useWidgets";

import {
  SidebarInset,
  SidebarProvider,
  SkipToMain,
} from "@repo/ui/components";

export default function CopilotKitPage() {
  const [themeColor] = useState("#6366f1");
  const { widgets } = useWidgets();

  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
      <SidebarProvider>
        {/* 与管理后台一致的 Sidebar 外观与交互 */}
        <ChatHistorySidebar />

        {/* 使用 SidebarInset 与 variant="inset" 保持布局一致 */}
        <SidebarInset id="main-content" className="flex">
          <div className="relative flex w-full">
            <MainContent widgets={widgets} />
            <CopilotSidebar
              clickOutsideToClose={false}
              defaultOpen={true}
              labels={{
                title: "Popup Assistant",
                initial: "👋 Select a conversation or start a new one!",
              }}
            />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </main>
  );
}
