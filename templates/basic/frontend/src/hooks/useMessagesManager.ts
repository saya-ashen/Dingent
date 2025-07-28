'use client';

import {
    Message,
    ActionExecutionMessage,
    loadMessagesFromJsonRepresentation,
} from "@copilotkit/runtime-client-gql";
import { useMemo, useState, useEffect, useRef } from "react";

import { Widget } from "@/types";

import { useCopilotMessagesContext, } from "@copilotkit/react-core";
import { useCopilotContext } from "@copilotkit/react-core";
import { useThreadContext } from "@/contexts/ThreadProvider";
type FetchedResource = Omit<Widget, 'payload'> & { payload: any, id: string };


export function useMessagesManager() {
    const { messages, setMessages } = useCopilotMessagesContext();
    const { threadId, agentSession, runtimeClient } = useCopilotContext();
    const { threads, updateThreadTitle } = useThreadContext();

    const [widgets, setWidgets] = useState<Widget[]>([]);

    const lastLoadedThreadId = useRef<string>("");
    const lastLoadedAgentName = useRef<string>("");
    const lastLoadedMessages = useRef<string>("");

    useEffect(() => {
        // 关键检查：如果 threadId 或 agentName 没有变化，则不重新获取
        if (
            !threadId ||
            !agentSession?.agentName ||
            (threadId === lastLoadedThreadId.current && agentSession.agentName === lastLoadedAgentName.current)
        ) {
            return;
        }

        const fetchMessages = async () => {
            // 检查 agentName 是否存在
            if (!agentSession?.agentName) return;

            const result = await runtimeClient.loadAgentState({
                threadId,
                agentName: agentSession.agentName,
            });

            // 错误处理
            if (result.error) {
                console.error("Failed to load agent state:", result.error);
                // 更新 ref 防止无限重试失败的请求
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentSession.agentName;
                return;
            }

            const newMessages = result.data?.loadAgentState?.messages;


            if (result.data?.loadAgentState?.threadExists) {
                // 更新 ref 标记已加载成功
                lastLoadedMessages.current = newMessages || "";
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentSession.agentName;

                const parsedMessages = loadMessagesFromJsonRepresentation(JSON.parse(newMessages || "[]"));
                setMessages(parsedMessages);
            }
            else {
                // 当线程不存在时，显式地清空消息列表
                setMessages([]);
                lastLoadedThreadId.current = threadId;
                lastLoadedAgentName.current = agentSession?.agentName;
            }
        };

        void fetchMessages(); // <--- 确保调用 fetch 函数！

    }, [threadId, agentSession?.agentName, runtimeClient, setMessages]);
    useEffect(() => {
        if (threadId !== lastLoadedThreadId.current) {
            return;
        }

        if (!threadId || !messages || messages.length === 0) {
            return;
        }

        const currentThread = threads.find(t => t.id === threadId);

        if (currentThread && currentThread.title === 'New Chat') {
            const firstUserMessage = messages.find((m): m is Message => m.role === 'user');

            if (firstUserMessage && firstUserMessage.content) {
                const newTitle = firstUserMessage.content.substring(0, 50);
                updateThreadTitle(threadId, newTitle);
            }
        }
    }, [messages, threadId, threads, updateThreadTitle]);

    useEffect(() => {
        const fetchWidgetData = async () => {
            // 1. Filter for the relevant messages that contain tool_output_ids. (Unchanged)
            const dataMessages = messages.filter(
                (message): message is ActionExecutionMessage =>
                    message.type === "ActionExecutionMessage" &&
                    message.name === "show_data" &&
                    !!message.arguments.tool_output_ids?.length
            );

            if (dataMessages.length === 0) {
                setWidgets([]); // No data messages, so clear any existing widgets.
                return;
            }

            try {
                // 2. Create promises that resolve to an array of widgets for each message.
                const widgetArraysPromises = dataMessages.map(async (message) => {
                    const resourceIds = message.arguments.tool_output_ids as string[];

                    // Fetch all resources, pairing each resource with its original ID.
                    const resourcePromises = resourceIds.map(async (id) => { // Make this function async
                        try {
                            const res = await fetch(`/api/resource/${id}`);
                            if (!res.ok) {
                                console.error(`Failed to fetch resource: ${id}`);
                                return null;
                            }
                            const resource = await res.json() as FetchedResource;
                            // Return an object containing both the id and the fetched resource.
                            return { id, resource };
                        } catch (error) {
                            console.error(`Error fetching or parsing resource ${id}:`, error);
                            return null;
                        }
                    });

                    // `Promise.all` will now resolve to an array of `{id, resource}` pairs or null.
                    const fetchedIdResourcePairs = (await Promise.all(resourcePromises)).filter(
                        // Update the type guard to reflect the new structure.
                        (pair): pair is { id: string; resource: FetchedResource } => pair !== null
                    );

                    // Map each pair to its own Widget object, using the preserved id.
                    return fetchedIdResourcePairs.map((pair): Widget => ({
                        id: pair.id, // CORRECT: Use the preserved ID from the pair.
                        type: pair.resource.type,
                        payload: pair.resource.payload,
                        metadata: pair.resource.metadata,
                    }));
                });

                // 4. Wait for all data to be fetched, then flatten the array of arrays.
                const resolvedWidgetArrays = await Promise.all(widgetArraysPromises);
                const flattenedWidgets = resolvedWidgetArrays.flat(); // Flatten [[w1, w2], [w3]] into [w1, w2, w3]

                console.log("resolvedWidgets", flattenedWidgets);
                setWidgets(flattenedWidgets);

            } catch (error) {
                console.error("An error occurred while fetching widget data:", error);
                setWidgets([]); // Clear widgets on error.
            }
        };

        void fetchWidgetData();
    }, [messages]);

    return { messages, widgets };
}

