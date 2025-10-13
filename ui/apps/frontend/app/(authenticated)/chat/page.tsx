"use client";

import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import React, { useState } from "react";
import { MainContent } from "@/components/MainContent";
import { useWidgets } from "@/hooks/useWidgets";

import { ChevronDown, X } from "lucide-react";
import { useActiveWorkflowId, useSetActiveWorkflowId, useWorkflow, useWorkflowsList } from "@repo/store";
import { WorkflowSummary } from "@repo/api-client";
import { useMessagesManager } from "@/hooks/useMessagesManager";


const WorkflowSelector: React.FC<{
  workflows: WorkflowSummary[];
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  isLoading: boolean;
}> = ({ workflows, activeId, setActiveId, isLoading }) => (
  <div className="flex items-center gap-2">
    <span className="text-sm text-gray-400">Workflow</span>
    <div className="relative">
      <select
        value={activeId ?? ""}
        onChange={(e) => setActiveId(e.target.value || null)}
        disabled={isLoading}
        className="appearance-none rounded-md border border-neutral-700 bg-neutral-800 px-3 py-1.5 pr-8 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-60"
        aria-label="Select a workflow"
      >
        <option value="" disabled>
          {isLoading ? "Loading..." : "Select workflow..."}
        </option>
        {workflows.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
        aria-hidden="true"
      />
    </div>
  </div>
);

// Sub-component for displaying the workflow description
// This encapsulates the toggle logic and state.
const WorkflowDetails: React.FC<{ description?: string }> = ({ description }) => {
  const [isOpen, setIsOpen] = useState(false);

  // Don't render anything if there's no description
  if (!description) {
    return null;
  }

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="text-xs text-gray-400 hover:text-gray-200 focus:outline-none"
        aria-expanded={isOpen}
        aria-controls="workflow-description"
      >
        {isOpen ? "Hide details" : "About this workflow"}
      </button>
      {/* A smooth transition for the details panel */}
      <div
        id="workflow-description"
        className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? "mt-1.5 max-h-96 opacity-100" : "max-h-0 opacity-0"
          }`}
      >
        <p className="text-xs text-gray-300 whitespace-pre-wrap">{description}</p>
      </div>
    </div>
  );
};

// Props type for the main header component.
type MyHeaderProps = {
  className?: string;
  onClose?: () => void;
};

// The main, refactored component.
// It is now much cleaner and acts as a container for the sub-components.
const MyHeader = ({ className = "", onClose }: MyHeaderProps) => {
  const { data: workflows = [], isLoading } = useWorkflowsList();
  const { data: activeId } = useActiveWorkflowId();
  const setActiveId = useSetActiveWorkflowId();
  const { data: workflow } = useWorkflow(activeId ?? null);
  // useMessagesManager()

  return (
    <header className={`px-4 py-3 border-b border-neutral-800 bg-neutral-900 ${className}`}>
      <div className="flex items-center justify-between">
        <WorkflowSelector
          workflows={workflows}
          activeId={activeId}
          setActiveId={setActiveId}
          isLoading={isLoading}
        />
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 rounded-full hover:bg-neutral-700/50 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-neutral-900 focus:ring-indigo-500"
            aria-label="Close assistant"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      <WorkflowDetails description={workflow?.description} />
    </header>
  );
};


export default function CopilotKitPage() {
  const [themeColor] = useState("#6366f1");
  const { widgets } = useWidgets();
  useMessagesManager()

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
          Header={MyHeader}
        />
      </div>
    </main>
  );
}
