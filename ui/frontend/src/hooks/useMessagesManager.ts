'use client';

import { useEffect, useMemo, useRef } from "react";
import {
    useCopilotMessagesContext,
    useCopilotContext,
} from "@copilotkit/react-core";
import {
    Message,
    loadMessagesFromJsonRepresentation,
} from "@copilotkit/runtime-client-gql";
import { useThreadContext } from "@/contexts/ThreadProvider";

/**
 * 只负责消息获取与标题更新
 */
export function useMessagesManager() {
    const { messages, setMessages } = useCopilotMessagesContext();
    const { threadId, agentSession, runtimeClient } = useCopilotContext();
    const { threads, updateThreadTitle } = useThreadContext();

    const lastLoadedThreadId = useRef<string>("");
    const lastLoadedAgentName = useRef<string>("");
    const lastLoadedMessages = useRef<string>("");

    const currentThread = useMemo(
        () => threads.find(t => t.id === threadId),
        [threads, threadId]
    );
    const threadRef = useRef(currentThread);

    useEffect(() => {
        threadRef.current = currentThread;
    }, [currentThread]);

    useEffect(() => {
        const agentName = agentSession?.agentName;
        if (
            !threadId ||
            !agentName ||
            (threadId === lastLoadedThreadId.current &&
                agentName === lastLoadedAgentName.current)
        ) {
            return;
        }

        let cancelled = false;

        const load = async () => {
            const result = await runtimeClient.loadAgentState({
                threadId,
                agentName,
            });
            if (cancelled) return;

            if (result.error) {
                console.error("Failed to load agent state:", result.error);
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentName;
                return;
            }

            const newMessages = result.data?.loadAgentState?.messages;
            const threadExists = result.data?.loadAgentState?.threadExists;

            if (threadExists) {
                lastLoadedMessages.current = newMessages || "";
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentName;
                try {
                    const parsed = loadMessagesFromJsonRepresentation(
                        JSON.parse(newMessages || "[]")
                    );
                    setMessages(parsed);
                } catch (e) {
                    console.error("Error parsing messages JSON:", e);
                    setMessages([]);
                }
            } else {
                setMessages([]);
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentName;
            }
        };

        void load();

        return () => {
            cancelled = true;
        };
    }, [threadId, agentSession?.agentName, runtimeClient, setMessages]);

    // 自动设置标题
    useEffect(() => {
        if (!messages?.length || !threadRef.current) return;
        const cur = threadRef.current;
        if (cur && cur.title === "New Chat") {
            const firstUserMessage = messages.find(
                (m): m is Message & { role: "user"; content: string } =>
                    "role" in m && (m as any).role === "user"
            );
            if (firstUserMessage?.content) {
                const newTitle = firstUserMessage.content.substring(0, 50).trim();
                if (newTitle) {
                    updateThreadTitle(cur.id, newTitle);
                }
            }
        }
    }, [messages, updateThreadTitle]);

    return { messages };
}
