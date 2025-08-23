'use client';

import {
    Message,
    ActionExecutionMessage,
    loadMessagesFromJsonRepresentation,
} from "@copilotkit/runtime-client-gql";
import { MarkdownPayload, TablePayload, Widget } from "@/types";
import { useMemo, useState, useEffect, useRef } from "react";


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


    // HACK: This is a hack to fix the issue where messages don't automatically refresh when creating a new conversation.
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

            const result = await runtimeClient.loadAgentState({
                threadId,
                agentName: agentSession.agentName,
            });

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

    }, [messages, updateThreadTitle]);
    const widgetIdDependency = useMemo(() => {
        const allIds = messages
            .filter(
                (message) =>
                    message.type === "ActionExecutionMessage" &&
                    "name" in message &&
                    message.name === "show_data" &&
                    'arguments' in message &&
                    typeof message.arguments === "object" &&
                    message.arguments !== null &&
                    "tool_output_id" in message.arguments &&
                    typeof message.arguments.tool_output_id === "string" &&
                    !!message.arguments.tool_output_id?.length
            )
            .flatMap((message) => 'arguments' in message &&
                typeof message.arguments === "object" &&
                message.arguments !== null &&
                "tool_output_id" in message.arguments &&
                typeof message.arguments.tool_output_id === "string" &&
                !!message.arguments.tool_output_id?.length && message.arguments.tool_output_id as string);

        const uniqueSortedIds = [...new Set(allIds)].sort();

        return JSON.stringify(uniqueSortedIds);
    }, [messages]);

    useEffect(() => {
        const fetchWidgetData = async () => {
            const dataMessages = messages.filter(
                (message): message is ActionExecutionMessage =>
                    message.type === "ActionExecutionMessage" &&
                    "name" in message && message.name === "show_data" &&
                    'arguments' in message &&
                    typeof message.arguments === "object" && message.arguments !== null && "tool_output_id" in message.arguments &&
                    typeof message.arguments.tool_output_id === "string" && !!message.arguments.tool_output_id?.length
            );

            if (dataMessages.length === 0) {
                setWidgets([]);
                return;
            }

            try {
                const widgetArraysPromises = dataMessages.map(async (message): Promise<Widget[]> => {
                    const resourceId = message.arguments.tool_output_id as string;

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
                console.log(flattenedWidgets)

                setWidgets(flattenedWidgets);
            } catch (error) {
                console.error("An error occurred while fetching widget data:", error);
                setWidgets([]);
            }
        };

        void fetchWidgetData();
    }, [widgetIdDependency]);


    return { messages, widgets };
}
