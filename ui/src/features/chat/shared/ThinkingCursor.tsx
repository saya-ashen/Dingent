import { useThinking } from "@/providers/ThinkingProvider";
import { BrainCircuit, Loader2, ChevronDown, ChevronRight } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { twMerge } from "tailwind-merge";
import { Streamdown } from "streamdown";

export function ThinkingCursor({ className }: { className?: string }) {
  const { thinkingText, isThinking } = useThinking();
  const [isExpanded, setIsExpanded] = useState(true);

  // 滚动容器的 Ref
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isThinking) {
      setIsExpanded(true);
    }
  }, [isThinking]);

  // 自动滚动逻辑：保持不变
  useEffect(() => {
    if (isExpanded && scrollRef.current) {
      const element = scrollRef.current;
      element.scrollTop = element.scrollHeight;
    }
  }, [thinkingText, isExpanded]);

  if (!isThinking) {
    return (
      <span
        className={twMerge(
          "inline-block w-1.5 h-4 ml-1 align-middle bg-zinc-900 dark:bg-zinc-100 animate-pulse",
          className,
        )}
      />
    );
  }

  if (!thinkingText) {
    return (
      <div
        className={twMerge(
          "flex items-center gap-2 text-muted-foreground text-sm py-2",
          className,
        )}
      >
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Thinking...</span>
      </div>
    );
  }

  return (
    <div className={twMerge("w-full max-w-full my-2", className)}>
      <div className="border border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-lg overflow-hidden transition-all duration-300">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100/50 dark:hover:bg-indigo-900/30 transition-colors"
        >
          <BrainCircuit className="w-4 h-4 animate-pulse" />
          <span>Thinking Process...</span>
          {isExpanded ? (
            <ChevronDown className="w-3 h-3 ml-auto" />
          ) : (
            <ChevronRight className="w-3 h-3 ml-auto" />
          )}
        </button>

        {isExpanded && (
          <div
            ref={scrollRef}
            className="px-3 py-2 text-xs text-zinc-600 dark:text-zinc-400 bg-white/50 dark:bg-black/20 border-t border-indigo-100 dark:border-indigo-900/30 max-h-[300px] overflow-y-auto scroll-smooth"
          >
            {/* [修改] 使用 Streamdown 
              注意：Streamdown 默认会处理 prose 样式，
              但我们通常还是保留外层的 prose 类以防万一，或者依赖 Streamdown 内部的默认样式。
              Streamdown 会自动处理未闭合的 Markdown 标签，不会再报错了。
            */}
            <div className="prose prose-sm prose-zinc dark:prose-invert max-w-none animate-in fade-in duration-300 leading-relaxed">
              <Streamdown>{thinkingText}</Streamdown>
              {/* 如果你发现 Streamdown 已经自带了闪烁光标（新版特性），
                可以将下面这行 span 删掉。
              */}
              <span className="inline-block w-1.5 h-3 ml-0.5 bg-indigo-400 animate-pulse align-middle" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
