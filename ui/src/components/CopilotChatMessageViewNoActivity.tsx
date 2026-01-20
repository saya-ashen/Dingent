import { ThinkingCursor } from "@/features/chat/shared/ThinkingCursor";
import {
  CopilotChatMessageView,
  CopilotChatMessageViewProps,
} from "@copilotkit/react-core/v2";

import { useMemo } from "react";

const CopilotChatMessageViewNoActivityImpl = (
  props: CopilotChatMessageViewProps,
) => {
  const filteredMessages = useMemo(() => {
    return props.messages?.filter((m) => m.role !== "activity") || [];
  }, [props.messages]);

  return (
    <CopilotChatMessageView
      {...props}
      messages={filteredMessages}
      cursor={ThinkingCursor}
    />
  );
};

CopilotChatMessageViewNoActivityImpl.Cursor = CopilotChatMessageView.Cursor;

export const CopilotChatMessageViewNoActivity =
  CopilotChatMessageViewNoActivityImpl as typeof CopilotChatMessageView;
