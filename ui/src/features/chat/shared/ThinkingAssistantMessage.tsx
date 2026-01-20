import React, { useState } from "react";
import { Streamdown } from "streamdown";
import { ChevronDown, ChevronRight, BrainCircuit } from "lucide-react";
import { useThinking } from "@/providers/ThinkingProvider";
import { twMerge } from "tailwind-merge";
import { CopilotChatAssistantMessage } from "@copilotkit/react-core/v2";

// 1. 定义思考过程的 UI 组件
const ThinkingDisclosure = ({ content }: { content: string }) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!content) return null;

  return (
    <div className="mb-4 border border-zinc-200 dark:border-zinc-800 rounded-md overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-zinc-50 dark:bg-zinc-900/50 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors text-xs font-medium text-zinc-500"
      >
        <BrainCircuit className="size-3.5" />
        <span>Thinking Process</span>
        {isOpen ? (
          <ChevronDown className="size-3.5 ml-auto" />
        ) : (
          <ChevronRight className="size-3.5 ml-auto" />
        )}
      </button>

      {isOpen && (
        <div className="px-3 py-3 bg-zinc-50/50 dark:bg-zinc-950/30 text-zinc-600 dark:text-zinc-400 text-sm leading-relaxed border-t border-zinc-200 dark:border-zinc-800 animate-in slide-in-from-top-2 fade-in duration-200">
          {/* 这里简单渲染文本，也可以用 Streamdown 渲染 markdown 格式的思考 */}
          <div className="whitespace-pre-wrap font-mono text-xs opacity-90">
            {content}
          </div>
        </div>
      )}
    </div>
  );
};

// 2. 自定义 Markdown Renderer
// 这个组件会替换 CopilotChatAssistantMessage 默认的 MarkdownRenderer

// 3. 封装 Assistant Message 组件
export function ThinkingAssistantMessage(
  props: React.ComponentProps<typeof CopilotChatAssistantMessage>,
) {
  const { thinkingText } = useThinking();
  const thought = thinkingText;

  // 我们自定义一个 MarkdownRenderer，利用闭包直接获取当前 message 的 thought
  const CustomRenderer = ({ content, className, ...rest }: any) => (
    <div className="w-full">
      {/* 如果有思考内容，先显示思考内容 */}
      {thought && <ThinkingDisclosure content={thought} />}

      {/* 然后显示正式回复 */}
      <CopilotChatAssistantMessage.MarkdownRenderer
        content={content}
        className={className}
        {...rest}
      />
    </div>
  );

  return (
    <CopilotChatAssistantMessage
      {...props}
      markdownRenderer={CustomRenderer} // 注入我们的自定义渲染器
    />
  );
}
