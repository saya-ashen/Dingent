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


export interface MarkdownPayload {
    type: "markdown";
    content: string;
    [k: string]: unknown;
}

export interface TablePayload {
    type: "table";
    columns: string[];
    rows: unknown[][];
    [k: string]: unknown;
}

export type WidgetPayload = MarkdownPayload | TablePayload;

export interface Widget {
    id: string;          // resourceId
    type: string;        // payload type, fallback 'markdown'
    payload: WidgetPayload;
    metadata?: unknown;
}
