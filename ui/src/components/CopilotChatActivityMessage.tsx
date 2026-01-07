import React from "react";
import { ActivityMessage } from "@ag-ui/core";
import { twMerge } from "tailwind-merge";
import { useRenderActivityMessage } from "@copilotkit/react-core/v2";

/**
 * 内部使用的 Memoized 组件
 * 保持这个 Wrapper 存在，是为了确保列表中单个未变化的消息不会因为父组件重渲染而重绘
 */
const MemoizedActivityMessage = React.memo(
  function MemoizedActivityMessage({
    message,
    renderActivityMessage,
  }: {
    message: ActivityMessage;
    renderActivityMessage: (
      message: ActivityMessage,
    ) => React.ReactElement | null;
  }) {
    return renderActivityMessage(message);
  },
  (prevProps, nextProps) => {
    // 性能优化逻辑：只在 ID、类型或内容变化时重新渲染
    if (prevProps.message.id !== nextProps.message.id) return false;
    if (prevProps.message.activityType !== nextProps.message.activityType)
      return false;
    if (
      JSON.stringify(prevProps.message.content) !==
      JSON.stringify(nextProps.message.content)
    )
      return false;
    return true;
  },
);

export interface CopilotChatActivityListProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * 接收 Activity 消息数组
   */
  messages: ActivityMessage[];
}

/**
 * 专门用于渲染 Activity 消息列表的组件
 */
export function CopilotChatActivityList({
  messages,
  className,
  ...props
}: CopilotChatActivityListProps) {
  // 获取渲染逻辑的 Hook
  const renderActivityMessage = useRenderActivityMessage();

  // 如果没有渲染函数或数组为空，不渲染任何内容
  if (!renderActivityMessage || !messages || messages.length === 0) {
    return null;
  }

  return (
    <div className={twMerge("flex flex-col gap-2", className)} {...props}>
      {messages.map((message) => (
        <MemoizedActivityMessage
          key={message.id}
          message={message}
          renderActivityMessage={renderActivityMessage}
        />
      ))}
    </div>
  );
}
