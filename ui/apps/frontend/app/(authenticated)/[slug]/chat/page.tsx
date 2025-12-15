"use client";

import React, { useEffect, useRef, useState, useLayoutEffect } from "react";
import { createPortal } from "react-dom"; // 引入 Portal
import { useParams } from "next/navigation";
import { ChevronDown, X, Info, Check, Workflow, Bot, Loader2 } from "lucide-react";
import { CopilotKitCSSProperties, CopilotSidebar, useChatContext } from "@copilotkit/react-ui";

import { MainContent } from "@/components/MainContent";
import { useWidgets } from "@/hooks/useWidgets";
import { useMessagesManager } from "@/hooks/useMessagesManager";
import { getClientApi } from "@/lib/api/client";

import { useWorkflowsList, useActiveWorkflow } from "@repo/store";
import { WorkflowSummary } from "@repo/api-client";

// --- Utility: Click Outside ---
function useClickOutside(ref: React.RefObject<HTMLDivElement>, triggerRef: React.RefObject<HTMLButtonElement>, handler: () => void) {
  useEffect(() => {
    const listener = (event: MouseEvent | TouchEvent) => {
      // 如果点击的是下拉菜单内部，或者触发按钮本身，则不关闭
      if (
        !ref.current ||
        ref.current.contains(event.target as Node) ||
        triggerRef.current?.contains(event.target as Node)
      ) {
        return;
      }
      handler();
    };
    document.addEventListener("mousedown", listener);
    document.addEventListener("touchstart", listener);
    return () => {
      document.removeEventListener("mousedown", listener);
      document.removeEventListener("touchstart", listener);
    };
  }, [ref, triggerRef, handler]);
}

// --- Component: WorkflowSelector (Optimized) ---
const WorkflowSelector: React.FC<{
  workflows: WorkflowSummary[];
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  isLoading: boolean;
}> = ({ workflows, activeId, setActiveId, isLoading }) => {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [coords, setCoords] = useState({ top: 0, left: 0, width: 0 });

  useClickOutside(dropdownRef as React.RefObject<HTMLDivElement>, buttonRef as React.RefObject<HTMLButtonElement>, () => setIsOpen(false));
  const updatePosition = () => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setCoords({ top: rect.bottom + 4, left: rect.left, width: rect.width }); // 距离更近 +4px
    }
  };
  useLayoutEffect(() => {
    if (isOpen) {
      updatePosition();
      window.addEventListener("scroll", updatePosition);
      window.addEventListener("resize", updatePosition);
    }
    return () => {
      window.removeEventListener("scroll", updatePosition);
      window.removeEventListener("resize", updatePosition);
    };
  }, [isOpen]);

  const activeWorkflow = workflows.find((w) => w.id === activeId);
  const handleSelect = (id: string) => {
    setActiveId(id);
    setIsOpen(false);
  };

  return (
    <>
      {/* Trigger Button - 修改重点: 扁平化设计 */}
      <button
        ref={buttonRef}
        onClick={() => !isLoading && setIsOpen(!isOpen)}
        disabled={isLoading || workflows.length === 0}
        className={`
          group relative flex items-center gap-2.5 px-2 py-1.5 -ml-2 rounded-lg
          transition-all duration-200 text-left max-w-full
          ${isOpen
            ? "bg-neutral-800/80 text-neutral-200"
            : "bg-transparent hover:bg-neutral-800/50 text-neutral-400 hover:text-neutral-200"}
        `}
      >
        {/* Icon: 更小，颜色更淡 */}
        <div className={`
          flex items-center justify-center w-7 h-7 rounded-md transition-colors
          ${isOpen ? "bg-indigo-500 text-white shadow-sm" : "bg-neutral-800/50 text-neutral-400 group-hover:bg-neutral-700 group-hover:text-neutral-200"}
        `}>
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Bot className="w-3.5 h-3.5" />
          )}
        </div>

        {/* Text Area: 紧凑布局 */}
        <div className="flex flex-col">
          <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 leading-tight group-hover:text-neutral-400">
            Current Workflow
          </span>
          <div className="flex items-center gap-1">
            <span className={`text-sm font-semibold truncate max-w-[160px] ${isOpen ? "text-white" : "text-neutral-200"}`}>
              {isLoading
                ? "Loading..."
                : workflows.length === 0
                  ? "No workflows"
                  : activeWorkflow?.name || "Select Workflow"}
            </span>
            <ChevronDown
              className={`w-3.5 h-3.5 opacity-50 transition-transform duration-200 ${isOpen ? "rotate-180 opacity-100" : ""}`}
            />
          </div>
        </div>
      </button>

      {/* Dropdown Menu (Portal) - 保持不变，但稍微调整位置 */}
      {isOpen && typeof document !== "undefined" && createPortal(
        <div
          ref={dropdownRef}
          style={{
            position: "fixed",
            top: coords.top,
            left: coords.left,
            width: Math.max(coords.width, 240),
            zIndex: 99999,
          }}
          className="animate-in fade-in zoom-in-95 slide-in-from-top-2 duration-150"
        >
          <div className="p-1 rounded-lg border border-neutral-800 bg-neutral-900 shadow-xl shadow-black/50 ring-1 ring-white/5 overflow-hidden">
            <div className="max-h-[280px] overflow-y-auto custom-scrollbar">
              {workflows.map((w) => {
                const isActive = activeId === w.id;
                return (
                  <button
                    key={w.id}
                    onClick={() => handleSelect(w.id)}
                    className={`
                      w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-left transition-colors
                      ${isActive
                        ? "bg-neutral-800 text-white font-medium"
                        : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200"}
                    `}
                  >
                    <Workflow className={`w-4 h-4 ${isActive ? "text-indigo-400" : "opacity-50"}`} />
                    <span className="flex-1 truncate">{w.name}</span>
                    {isActive && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
};

// --- Component: WorkflowDetails (Styled) ---
const WorkflowDetails: React.FC<{ description?: string }> = ({ description }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!description) return null;

  return (
    <div className="px-4 -mt-1">
      {/* 这是一个带有动画的容器 */}
      <div
        className={`
          grid transition-all duration-300 ease-in-out overflow-hidden
          ${isOpen ? "grid-rows-[1fr] opacity-100 mb-1.5" : "grid-rows-[0fr] opacity-0 mb-0"}
        `}
      >
        <div className="min-h-0"> {/* min-h-0 是 grid 动画的关键 */}
          <div className="pb-2 rounded-md border border-indigo-500/10 bg-indigo-500/5 text-[11px] text-neutral-300 leading-snug shadow-inner">
            <span className="text-indigo-400 font-semibold mr-1">Info:</span>
            {description}
          </div>
        </div>
      </div>

      {/* 控制按钮 */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className={`
          flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide transition-colors
          ${isOpen ? "text-indigo-400" : "text-neutral-600 hover:text-neutral-400"}
        `}
      >
        <Info className="w-3 h-3" />
        {isOpen ? "Hide Details" : "Details"}
      </button>
    </div>
  );
};

// --- Component: MyHeader (Main) ---
type MyHeaderProps = {
  className?: string;
};

const MyHeader = ({ className = "", }: MyHeaderProps) => {
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi().forWorkspace(slug);
  const { setOpen } = useChatContext();

  const workflowsQ = useWorkflowsList(api.workflows);
  const { id: activeId, setActiveId, workflow } = useActiveWorkflow(api.workflows);
  const workflows = workflowsQ.data || [];

  return (
    <header className={`
      flex flex-col border-b border-neutral-800 bg-neutral-950
      ${className}
    `}>
      {/* 主行：固定高度，flex 居中
        px-4: 左右间距适中
        h-14: 56px 高度，标准 Header 高度
      */}
      <div className="flex items-center justify-between px-4 h-14 w-full">
        {/* 左侧选择器 */}
        <div className="flex-1 min-w-0 mr-2">
          <WorkflowSelector
            workflows={workflows}
            activeId={activeId}
            setActiveId={setActiveId}
            isLoading={workflowsQ.isLoading}
          />
        </div>

        {/* 右侧关闭按钮 */}
        {setOpen && (
          <button
            onClick={() => setOpen(false)}
            className="flex items-center justify-center w-8 h-8 rounded-md text-neutral-500 hover:bg-neutral-800 hover:text-neutral-200 transition-colors"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {workflow?.description && (
        <div className="px-4 pb-2 -mt-1">
          <WorkflowDetails description={workflow?.description} />
        </div>
      )}
    </header>
  );
};

export default function CopilotKitPage() {
  const [themeColor] = useState("#6366f1");
  const { widgets } = useWidgets();

  useMessagesManager();

  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
      <div className="relative flex w-full h-full">
        <MainContent widgets={widgets} />
        <CopilotSidebar
          clickOutsideToClose={false}
          defaultOpen={true}
          imageUploadsEnabled={true}
          inputFileAccept={"image/*"}
          labels={{
            title: "Dingent Assistant",
            initial: "👋 Select a workflow to start working!",
          }}
          Header={MyHeader}
        />
      </div>
    </main>
  );
}
