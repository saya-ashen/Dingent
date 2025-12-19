import React, { useRef, useState } from "react";
import { ChevronDown, Workflow, Check, Bot, Loader2 } from "lucide-react";
import { useClickOutside } from "@/hooks/use-click-outside";
import { WorkflowSummary } from "@/types/entity";

interface WorkflowSelectorProps {
  workflows: WorkflowSummary[];
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  isLoading: boolean;
}

export const WorkflowSelector: React.FC<WorkflowSelectorProps> = ({
  workflows,
  activeId,
  setActiveId,
  isLoading,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useClickOutside(dropdownRef, () => setIsOpen(false), buttonRef);

  const activeWorkflow = workflows.find((w) => w.id === activeId);

  const handleSelect = (id: string) => {
    setActiveId(id);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      {/* 触发按钮：设计为更紧凑的胶囊样式 */}
      <button
        ref={buttonRef}
        onClick={() => !isLoading && setIsOpen(!isOpen)}
        disabled={isLoading || workflows.length === 0}
        className={`
          group flex items-center gap-2 pl-1 pr-3 py-1 rounded-full border transition-all duration-200
          ${isOpen
            ? "bg-neutral-800 border-neutral-700 text-neutral-200"
            : "bg-neutral-900/50 border-neutral-800 hover:border-neutral-700 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800"}
        `}
      >
        {/* 图标容器 */}
        <div className={`
          flex items-center justify-center w-6 h-6 rounded-full transition-colors
          ${isOpen ? "bg-indigo-500/20 text-indigo-400" : "bg-neutral-800 text-neutral-500 group-hover:text-neutral-300"}
        `}>
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Bot className="w-3.5 h-3.5" />
          )}
        </div>

        {/* 文本区域 */}
        <div className="flex flex-col items-start text-left mr-1">
          <span className="text-[10px] uppercase font-bold text-neutral-600 leading-none mb-0.5 group-hover:text-neutral-500 transition-colors">
            Agent
          </span>
          <span className="text-xs font-medium truncate max-w-[120px] sm:max-w-[160px] leading-none">
            {isLoading
              ? "Loading..."
              : workflows.length === 0
                ? "No workflows"
                : activeWorkflow?.name || "Select Workflow"}
          </span>
        </div>

        <ChevronDown
          className={`w-3.5 h-3.5 ml-1 opacity-50 transition-transform duration-200 ${isOpen ? "rotate-180 opacity-100" : ""}`}
        />
      </button>

      {/* 下拉菜单：绝对定位，带毛玻璃和阴影 */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 mt-2 w-64 z-50 animate-in fade-in zoom-in-95 slide-in-from-top-1 duration-150"
        >
          <div className="p-1 rounded-xl border border-neutral-800 bg-neutral-900/95 backdrop-blur-xl shadow-2xl shadow-black/80 ring-1 ring-white/5">
            <div className="max-h-[280px] overflow-y-auto custom-scrollbar">
              {workflows.map((w) => {
                const isActive = activeId === w.id;
                return (
                  <button
                    key={w.id}
                    onClick={() => handleSelect(w.id)}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-left transition-all
                      ${isActive
                        ? "bg-neutral-800 text-white font-medium shadow-sm"
                        : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200"}
                    `}
                  >
                    <Workflow className={`w-4 h-4 ${isActive ? "text-indigo-400" : "opacity-40"}`} />
                    <span className="flex-1 truncate">{w.name}</span>
                    {isActive && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                  </button>
                );
              })}
              {workflows.length === 0 && (
                <div className="px-4 py-3 text-xs text-neutral-500 text-center">
                  No workflows available
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
