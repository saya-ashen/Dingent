import React, { useState } from "react";
import { Info } from "lucide-react";

export const WorkflowDetails: React.FC<{ description?: string }> = ({ description }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!description) return null;

  return (
    <div className="relative group">
      {/* 折叠内容 */}
      <div
        className={`
          grid transition-all duration-300 ease-out overflow-hidden
          ${isOpen ? "grid-rows-[1fr] opacity-100 mt-2" : "grid-rows-[0fr] opacity-0 mt-0"}
        `}
      >
        <div className="min-h-0">
          <div className="p-3 rounded-lg border border-indigo-500/20 bg-indigo-500/5 text-xs text-indigo-200/80 leading-relaxed shadow-inner">
            <span className="text-indigo-400 font-semibold mr-1">About this agent:</span>
            {description}
          </div>
        </div>
      </div>

      {/* 控制按钮 - 放在底部或侧边根据布局决定，这里做成 toggle 形式 */}
      <div className="flex justify-start mt-1">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`
            flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors px-2 py-0.5 rounded-md
            ${isOpen
              ? "text-indigo-400 bg-indigo-500/10"
              : "text-neutral-600 hover:text-neutral-400 hover:bg-neutral-800/50"}
          `}
        >
          <Info className="w-3 h-3" />
          {isOpen ? "Hide Info" : "Info"}
        </button>
      </div>
    </div>
  );
};
