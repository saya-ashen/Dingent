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
    const titleUpdatedRef = useRef(false);

    useEffect(() => {
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
        // 当我们切换到新的聊天时，需要重置标记，以便为新聊天设置标题
        titleUpdatedRef.current = false;
    }, [threadId]);
    useEffect(() => {
        if (titleUpdatedRef.current || !threadId || !messages || messages.length === 0) {
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
    const widgetIdDependency = useMemo(() => {
        const allIds = messages
            .filter(
                (message): message is ActionExecutionMessage =>
                    message.type === "ActionExecutionMessage" &&
                    message.name === "show_data" &&
                    !!message.arguments.tool_output_ids?.length
            )
            .flatMap((message) => message.arguments.tool_output_ids as string[]);

        // 排序以确保顺序稳定
        const uniqueSortedIds = [...new Set(allIds)].sort();

        // 转换成 JSON 字符串，这是一个稳定的原始类型值
        return JSON.stringify(uniqueSortedIds);
    }, [messages]);

    useEffect(() => {
        const fetchWidgetData = async () => {
            const dataMessages = messages.filter(
                (message): message is ActionExecutionMessage =>
                    message.type === "ActionExecutionMessage" &&
                    message.name === "show_data" &&
                    !!message.arguments.tool_output_ids?.length
            );

            if (dataMessages.length === 0) {
                setWidgets([]);
                return;
            }

            try {
                const widgetArraysPromises = dataMessages.map(async (message) => {
                    const resourceIds = message.arguments.tool_output_ids as string[];
                    const resourcePromises = resourceIds.map(async (id) => {
                        try {
                            const res = await fetch(`/api/resource/${id}`);
                            if (!res.ok) {
                                console.error(`Failed to fetch resource: ${id}`);
                                return null;
                            }
                            const resource = await res.json() as FetchedResource;
                            return { id, resource };
                        } catch (error) {
                            console.error(`Error fetching or parsing resource ${id}:`, error);
                            return null;
                        }
                    });
                    const fetchedIdResourcePairs = (await Promise.all(resourcePromises)).filter(
                        (pair): pair is { id: string; resource: FetchedResource } => pair !== null
                    );
                    return fetchedIdResourcePairs.map((pair): Widget => ({
                        id: pair.id,
                        type: pair.resource.type,
                        payload: pair.resource.payload,
                        metadata: pair.resource.metadata,
                    }));
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
    }, [widgetIdDependency]);


    return { messages, widgets };
}

