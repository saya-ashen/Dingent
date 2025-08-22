import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useCopilotChat } from "@copilotkit/react-core";
import { ThreadContextType, ChatThread } from '@/types'; // Import from types file


// Create Context
export const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

// Create a custom Hook for convenience
export const useThreadContext = () => {
    const context = useContext(ThreadContext);
    if (!context) {
        throw new Error("useThreadContext must be used within a ThreadProvider (in Providers component)");
    }
    return context;
};

const THREAD_LIST_KEY = 'chatThreadIdList';
const CURRENT_THREAD_ID_KEY = 'currentChatThreadId';

export function useThreadManager() {
    const {
        isLoading: isChatProcessing,
    } = useCopilotChat();

    const { activeThreadId, setActiveThreadId } = useThreadContext();

    const [threads, setThreads] = useState<ChatThread[]>([]);
    const [isInitializing, setIsInitializing] = useState(true);

    // Effect to initialize thread list from localStorage
    useEffect(() => {
        // Define an async function inside the useEffect hook
        const initialize = async () => {
            try {
                const storedList: ChatThread[] = JSON.parse(localStorage.getItem(THREAD_LIST_KEY) || '[]');
                setThreads(storedList);

                if (!activeThreadId && storedList.length === 0) {
                    const newId = uuidv4();
                    setActiveThreadId(newId);
                }
            } catch (error) {
                console.error("Initialization failed:", error);
                setThreads([])
            } finally {
                setIsInitializing(false);
            }
        };

        // Call the async function
        initialize();

    }, []);


    useEffect(() => {
        if (!activeThreadId || isInitializing) {
            return;
        }

        localStorage.setItem(CURRENT_THREAD_ID_KEY, activeThreadId);

        setThreads(prevThreads => {
            const threadExists = prevThreads.some(thread => thread.id === activeThreadId);
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
        setThreads(prevThreads => {
            const newThreads = prevThreads.map(thread =>
                thread.id === id ? { ...thread, title } : thread
            );
            localStorage.setItem(THREAD_LIST_KEY, JSON.stringify(newThreads));
            return newThreads;
        });
    }, []);

    const deleteAllThreads = () => {
        // Create a new thread to start with
        const newId = uuidv4();
        const newThread: ChatThread = { id: newId, title: "New Chat" };

        // Reset the threads state to only contain the new thread
        setThreads([newThread]);
        // Update localStorage with the new list
        localStorage.setItem(THREAD_LIST_KEY, JSON.stringify([newThread]));

        // Set the new thread as the active one
        setActiveThreadId(newId);
        // localStorage for CURRENT_THREAD_ID_KEY will be updated by the useEffect
    };
    return {
        isLoading: isInitializing || isChatProcessing,
        threads, // Changed from threadIds
        activeThreadId: activeThreadId || '',
        setActiveThreadId,
        updateThreadTitle, // Expose the new function
        deleteAllThreads,
    };
}
