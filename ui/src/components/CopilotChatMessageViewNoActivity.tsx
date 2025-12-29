import {
  CopilotChatMessageView,
  CopilotChatMessageViewProps,
} from "@copilotkit/react-core/v2";
import React, { useMemo } from "react";

// 1. 定义组件实现
const CopilotChatMessageViewNoActivityImpl = (
  props: CopilotChatMessageViewProps,
) => {
  const filteredMessages = useMemo(() => {
    return props.messages?.filter((m) => m.role !== "activity") || [];
  }, [props.messages]);

  return <CopilotChatMessageView {...props} messages={filteredMessages} />;
};

// 2. 挂载静态属性 (这一步为了运行时正常工作)
CopilotChatMessageViewNoActivityImpl.Cursor = CopilotChatMessageView.Cursor;

// 3. 导出并强制转换类型 (这一步为了解决 TypeScript 报错)
// 我们告诉 TS：这个组件就是 CopilotChatMessageView 的类型
export const CopilotChatMessageViewNoActivity =
  CopilotChatMessageViewNoActivityImpl as typeof CopilotChatMessageView;
