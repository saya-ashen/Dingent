"use client";

import {
  useState,
  useEffect,
  createContext,
  useContext,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import { v4 as uuidv4 } from "uuid";
import { ThreadContextType, ChatThread } from "@repo/types";
import { getClientApi } from "@/lib/api/client";
import { useParams } from "next/navigation";

const CURRENT_THREAD_ID_KEY = "currentChatThreadId";

interface ExtendedThreadContextType extends ThreadContextType {
  deleteThread: (id: string) => Promise<void>; // 变为异步
  createThread: () => void;
  refreshThreads: () => Promise<void>; // 新增：手动刷新列表
}

export const ThreadContext = createContext<ExtendedThreadContextType | undefined>(undefined);

export const useThreadContext = () => {
  const context = useContext(ThreadContext);
  if (!context) {
    throw new Error("useThreadContext must be used within a ThreadProvider");
  }
  return context;
};

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string>("");
  const [isInitializing, setIsInitializing] = useState(true);
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi().forWorkspace(slug);

  const fetchThreads = useCallback(async () => {
    try {
      // 直接调用封装好的 SDK
      const threads = await api.threads.list();

      // 【关键】: 如果前端组件强依赖 camelCase (createdAt)，在这里做一层映射
      // 如果前端可以直接改用 snake_case，则不需要这步
      return threads.map(t => ({
        id: t.id,
        title: t.title,
        createdAt: new Date(t.created_at), // 转换字符串为 Date 对象
        updatedAt: new Date(t.updated_at)
      }));
    } catch (error) {
      console.error("Failed to fetch threads", error);
      return [];
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    const init = async () => {
      setIsInitializing(true);
      const serverThreads = await fetchThreads();

      if (!mounted) return;

      setThreads(serverThreads);

      // 恢复上次选中的 ID
      const lastActiveId = localStorage.getItem(CURRENT_THREAD_ID_KEY);

      if (lastActiveId && serverThreads.some((t) => t.id === lastActiveId)) {
        // 如果本地存的 ID 在服务器列表里存在，就用它
        setActiveThreadId(lastActiveId);
      } else if (serverThreads.length > 0) {
        // 否则默认选中第一个
        setActiveThreadId(serverThreads[0].id);
      } else {
        // 如果服务器也没数据，创建一个全新的本地状态（此时还没存库）
        createNewLocalThread();
      }

      setIsInitializing(false);
    };

    init();

    return () => {
      mounted = false;
    };
  }, [fetchThreads]);

  const createNewLocalThread = useCallback(() => {
    const newId = uuidv4();
    const newThread: ChatThread = {
      id: newId,
      title: "New Chat",
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(newId);
    return newId;
  }, []);

  // --- 4. 监听 Active ID 变化并存储偏好 ---
  useEffect(() => {
    if (activeThreadId) {
      localStorage.setItem(CURRENT_THREAD_ID_KEY, activeThreadId);
    }
  }, [activeThreadId]);


  const createThread = useCallback(() => {
    createNewLocalThread();
  }, [createNewLocalThread]);

  const updateThreadTitle = useCallback(async (id: string) => {
    const latestThreads = await fetchThreads();
    setThreads(latestThreads);

  }, []);

  const deleteThread = useCallback(async (id: string) => {
    // 1. 乐观更新 UI (先删界面，显得快)
    const oldThreads = [...threads];
    setThreads((prev) => prev.filter((t) => t.id !== id));

    // 切换选中状态逻辑
    if (id === activeThreadId) {
      const remaining = oldThreads.filter(t => t.id !== id);
      if (remaining.length > 0) {
        setActiveThreadId(remaining[0].id);
      } else {
        createNewLocalThread();
      }
    }

    try {
      await api.threads.delete(id);
    } catch (error) {
      setThreads(oldThreads);
    }
  }, [threads, activeThreadId, createNewLocalThread]);

  const deleteAllThreads = useCallback(async () => {
    setThreads([]);
    createNewLocalThread();
    await api.threads.deleteAll();
  }, [createNewLocalThread]);

  const value = useMemo(
    () => ({
      isLoading: isInitializing,
      threads,
      activeThreadId,
      setActiveThreadId,
      createThread,
      updateThreadTitle,
      deleteThread,
      deleteAllThreads,
      refreshThreads: async () => {
        const data = await fetchThreads();
        setThreads(data);
      }
    }),
    [
      isInitializing,
      threads,
      activeThreadId,
      createThread,
      updateThreadTitle,
      deleteThread,
      deleteAllThreads,
      fetchThreads
    ]
  );

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}
