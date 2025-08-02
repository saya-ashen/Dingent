"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import React, { useState } from "react";
import "./style.css";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { MainContent } from "@/components/MainContent";
import { useMessagesManager } from "@/hooks/useMessagesManager";


export default function CopilotKitPage() {
    const [themeColor] = useState("#6366f1");
    const { widgets } = useMessagesManager();

    useCopilotAction({
        name: "show_data",
        description: "",
        parameters: [
            { name: "tool_output_ids", type: "string[]", description: "tool_output_ids", required: true },
        ],
        followUp: false,
        handler: async ({tool_output_ids}) => {
        },
    });

    return (
        <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
            {/* 4. Use flexbox for the main layout */}
            <div className="flex flex-row w-full h-screen">
                <ChatHistorySidebar /> {/* 5. Add the history sidebar */}

                {/* This container wraps your main content and the Copilot sidebar */}
                <div className="relative flex-grow flex">
                    <MainContent widgets={widgets} />
                    <CopilotSidebar
                        clickOutsideToClose={false}
                        defaultOpen={true}
                        labels={{
                            title: "Popup Assistant",
                            initial: "👋 Select a conversation or start a new one!"
                        }}
                    />
                </div>
            </div>
        </main>
    );
}
