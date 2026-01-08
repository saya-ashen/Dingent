"use client";

import { useEffect, useState } from "react";
import { ChatPage } from "@/features/chat/shared/ChatPage";

export default function GuestChatPage() {
  const [visitorId, setVisitorId] = useState<string>("");

  useEffect(() => {
    setVisitorId(localStorage.getItem("dingent_visitor_id") || "");
  }, []);

  if (!visitorId) return null;

  return <ChatPage isGuest={true} visitorId={visitorId} />;
}
