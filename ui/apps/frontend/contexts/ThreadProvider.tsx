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
// import { useCopilotChat } from "@copilotkit/react-core";
import { ThreadContextType, ChatThread } from "@repo/types";

const THREAD_LIST_KEY = "chatThreadIdList";
const CURRENT_THREAD_ID_KEY = "currentChatThreadId";

// Helper function to get initial ID safely on the client
const getInitialThreadId = (): string => {
  if (typeof window === "undefined") {
    return ""; // Return empty string SSR, will be updated on client
  }
  const storedList: ChatThread[] = JSON.parse(
    localStorage.getItem(THREAD_LIST_KEY) || "[]",
  );
  const lastActiveId = localStorage.getItem(CURRENT_THREAD_ID_KEY);

  if (lastActiveId && storedList.some((thread) => thread.id === lastActiveId)) {
    return lastActiveId;
  }
  return storedList[0]?.id || "";
};

export const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

export const useThreadContext = () => {
  const context = useContext(ThreadContext);
  if (!context) {
    throw new Error("useThreadContext must be used within a ThreadProvider");
  }
  return context;
};

// This is the component you will use in your main Providers file
export function ThreadProvider({ children }: { children: ReactNode }) {
  // const { isLoading: isChatProcessing } = useCopilotChat({
  //   id: "global-chat-handler"
  // });

  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string>("");
  const [isInitializing, setIsInitializing] = useState(true);

  // Initialize state from localStorage on client mount
  useEffect(() => {
    const initialId = getInitialThreadId();
    const storedList: ChatThread[] = JSON.parse(localStorage.getItem(THREAD_LIST_KEY) || "[]");

    setThreads(storedList);

    if (initialId) {
      setActiveThreadId(initialId);
    } else {
      // If no threads exist, create a new one
      const newId = uuidv4();
      setActiveThreadId(newId);
    }
    setIsInitializing(false);
  }, []);

  // Effect to manage thread list and persist active ID
  useEffect(() => {
    if (isInitializing || !activeThreadId) return;

    localStorage.setItem(CURRENT_THREAD_ID_KEY, activeThreadId);

    setThreads((prevThreads) => {
      const threadExists = prevThreads.some((thread) => thread.id === activeThreadId);
      if (!threadExists) {
        const newThread: ChatThread = { id: activeThreadId, title: "New Chat" };
        const newList = [newThread, ...prevThreads];
        localStorage.setItem(THREAD_LIST_KEY, JSON.stringify(newList));
        return newList;
      }
      return prevThreads;
    });
  }, [activeThreadId, isInitializing]);

  const updateThreadTitle = useCallback((id: string, title: string) => {
    setThreads((prevThreads) => {
      const newThreads = prevThreads.map((thread) =>
        thread.id === id ? { ...thread, title } : thread,
      );
      localStorage.setItem(THREAD_LIST_KEY, JSON.stringify(newThreads));
      return newThreads;
    });
  }, []);

  const deleteAllThreads = useCallback(() => {
    const newId = uuidv4();
    const newThread: ChatThread = { id: newId, title: "New Chat" };
    setThreads([newThread]);
    localStorage.setItem(THREAD_LIST_KEY, JSON.stringify([newThread]));
    setActiveThreadId(newId);
  }, []);

  const value = useMemo(
    () => ({
      isLoading: isInitializing,
      threads,
      activeThreadId,
      setActiveThreadId,
      updateThreadTitle,
      deleteAllThreads,
    }),
    [isInitializing, threads, activeThreadId, updateThreadTitle, deleteAllThreads]
  );

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}
