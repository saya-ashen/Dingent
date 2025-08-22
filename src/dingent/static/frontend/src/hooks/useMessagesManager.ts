'use client';

import {
    Message,
    ActionExecutionMessage,
    loadMessagesFromJsonRepresentation,
} from "@copilotkit/runtime-client-gql";
import { useMemo, useState, useEffect, useRef } from "react";

import { MarkdownPayload, TablePayload, Widget } from "@/types";

import { useCopilotMessagesContext, } from "@copilotkit/react-core";
import { useCopilotContext } from "@copilotkit/react-core";
import { useThreadContext } from "@/contexts/ThreadProvider";
type FetchedResource = Omit<Widget, 'payload'> & { payloads: unknown, metadata: unknown };


export function useMessagesManager() {
    const { messages, setMessages } = useCopilotMessagesContext();
    const { threadId, agentSession, runtimeClient } = useCopilotContext();
    const { threads, updateThreadTitle } = useThreadContext();

    const [widgets, setWidgets] = useState<Widget[]>([]);

    const lastLoadedThreadId = useRef<string>("");
    const lastLoadedAgentName = useRef<string>("");
    const lastLoadedMessages = useRef<string>("");
    const currentThread = useMemo(() => {
        return threads.find(t => t.id === threadId);
    }, [threads, threadId]);
    const threadRef = useRef(currentThread);

    // Effect for fetching initial messages when thread or agent changes
    useEffect(() => {
        if (
            !threadId ||
            !agentSession?.agentName ||
            (threadId === lastLoadedThreadId.current && agentSession.agentName === lastLoadedAgentName.current)
        ) {
            return;
        }

        const fetchMessages = async () => {
            if (!agentSession?.agentName) return;
            const result = await runtimeClient.loadAgentState({ threadId, agentName: agentSession.agentName });
            if (result.error) {
                console.error("Failed to load agent state:", result.error);
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentSession.agentName;
                return;
            }
            const newMessages = result.data?.loadAgentState?.messages;
            if (result.data?.loadAgentState?.threadExists) {
                lastLoadedMessages.current = newMessages || "";
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentSession.agentName;
                const parsedMessages = loadMessagesFromJsonRepresentation(JSON.parse(newMessages || "[]"));
                setMessages(parsedMessages);
            }
            else {
                setMessages([]);
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentSession?.agentName;
            }
        };

        void fetchMessages();
    }, [threadId, agentSession?.agentName, runtimeClient, setMessages]);

    // Effect for updating thread title from first message
    useEffect(() => {
        threadRef.current = currentThread;
    }, [currentThread]);
    useEffect(() => {
        if (!messages || messages.length === 0 || !threadRef.current) {
            return;
        }
        if (currentThread && currentThread.title === 'New Chat') {
            const firstUserMessage = messages.find(
                (m): m is Message & { role: 'user'; content: string } => 'role' in m && m.role === 'user'
            );
            if (firstUserMessage && firstUserMessage.content) {
                const newTitle = firstUserMessage.content.substring(0, 50);
                updateThreadTitle(threadRef.current.id, newTitle);
            }
        }
    }, [messages, updateThreadTitle, currentThread]);

    // Create a memoized array of only the specific action messages we need
    // using an INLINE type guard as requested.
    const showDataActionMessages = useMemo(() => {
        return messages.filter(
            (message): message is Message & {
                type: "ActionExecutionMessage";
                name: "show_data";
                arguments: { tool_output_id: string;[key: string]: unknown };
            } => {
                // First, check the `type` property. This should narrow the type for TypeScript.
                if (message.type !== "ActionExecutionMessage") {
                    return false;
                }
                // Now, safely check the other properties.
                const actionMessage = message as ActionExecutionMessage;
                return (
                    actionMessage.name === "show_data" &&
                    typeof actionMessage.arguments === "object" &&
                    actionMessage.arguments !== null &&
                    "tool_output_id" in actionMessage.arguments &&
                    typeof actionMessage.arguments.tool_output_id === "string"
                );
            }
        );
    }, [messages]);

    // Effect to fetch widget data, depending on the memoized array above.
    useEffect(() => {
        const fetchWidgetData = async () => {
            if (showDataActionMessages.length === 0) {
                setWidgets([]);
                return;
            }

            try {
                const widgetArraysPromises = showDataActionMessages.map(async (message): Promise<Widget[]> => {
                    // Because of the filter above, `message` is guaranteed to have the correct shape.
                    const resourceId = message.arguments.tool_output_id;

                    try {
                        const res = await fetch(`/api/resource/${resourceId}`);
                        if (!res.ok) {
                            console.error(`Failed to fetch resource: ${resourceId}, Status: ${res.status}`);
                            return [];
                        }

                        const resource = await res.json() as FetchedResource;

                        if (!resource || !Array.isArray(resource.payloads)) {
                            console.error(`Invalid resource structure for resourceId: ${resourceId}`);
                            return [];
                        }

                        return resource.payloads.map((payloadItem: TablePayload | MarkdownPayload): Widget => ({
                            id: resourceId,
                            type: payloadItem.type || "markdown",
                            payload: payloadItem,
                            metadata: resource.metadata
                        }));

                    } catch (error) {
                        console.error(`Error fetching or parsing resource ${resourceId}:`, error);
                        return [];
                    }
                });

                const resolvedWidgetArrays = await Promise.all(widgetArraysPromises);
                const flattenedWidgets = resolvedWidgetArrays.flat();
                setWidgets(flattenedWidgets);
            } catch (error) {
                console.error("An error occurred while fetching widget data:", error);
                setWidgets([]);
            }
        };

        void fetchWidgetData();
    }, [showDataActionMessages]);


    return { messages, widgets };
}
