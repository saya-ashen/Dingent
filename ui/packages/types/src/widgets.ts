import { Dispatch, SetStateAction } from "react";

export interface ChatThread {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface ThreadContextType {
  isLoading: boolean;
  threads: ChatThread[]; // Changed from threadIds: string[]
  activeThreadId: string | undefined;
  setActiveThreadId: Dispatch<SetStateAction<string>>;
  updateThreadTitle: (id: string) => void;
  deleteAllThreads: () => void;
  deleteThread: (id: string) => void;
}

export interface MarkdownPayload {
  type: "markdown";
  content: string;
  title?: string;
  [k: string]: unknown;
}

export interface TablePayload {
  type: "table";
  columns: string[];
  rows: unknown;
  title?: string;
  [k: string]: unknown;
}

export type WidgetPayload = MarkdownPayload | TablePayload;

export interface Widget {
  id: string; // resourceId
  type: string; // payload type, fallback 'markdown'
  payload: WidgetPayload;
  metadata?: unknown;
}
