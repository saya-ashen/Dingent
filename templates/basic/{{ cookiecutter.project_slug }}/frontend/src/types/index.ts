import { Dispatch, SetStateAction } from 'react';


export interface ChatThread {
    id: string;
    title: string;
}

export interface ThreadContextType {
    activeThreadId: string | undefined;
    setActiveThreadId: Dispatch<SetStateAction<string | undefined>>;
    isLoading?: boolean;
    threads: ChatThread[]; // Changed from threadIds: string[]
    deleteAllThreads: () => void;
    updateThreadTitle: (id: string, title: string) => void;
}

export interface TablePayload {
    columns: string[];
    rows: Record<string, string | number>[];
}
export interface MarkdownPayload {
    content: string;
}

export interface Widget {
    id: string;
    type: string;
    payload: TablePayload | MarkdownPayload;
    metadata?: {
    };
}
