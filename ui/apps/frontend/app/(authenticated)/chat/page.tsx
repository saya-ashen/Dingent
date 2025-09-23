"use client";

import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import React, { useState } from "react";
import { MainContent } from "@/components/MainContent";
import { useWidgets } from "@/hooks/useWidgets";

export default function CopilotKitPage() {
  const [themeColor] = useState("#6366f1");
  const { widgets } = useWidgets();

  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
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
    </main>
  );
}
