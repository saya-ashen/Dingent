'use client';

import React from 'react';
// --- CHANGE: Import useThreadContext instead of useThreadManager ---
import { useThreadContext } from "@/contexts/ThreadProvider";
import { v4 as uuidv4 } from 'uuid';

export function ChatHistorySidebar() {
    // --- CHANGE: Get the full context value ---
    const {
        threads, // This is now an array of {id, title}
        activeThreadId,
        setActiveThreadId,
        deleteAllThreads,
    } = useThreadContext();

    const handleNewChat = () => {
        const newId = uuidv4();
        setActiveThreadId(newId);
    };

    const handleDeleteAll = () => {
        if (window.confirm("Are you sure you want to delete all conversations? This action cannot be undone.")) {
            deleteAllThreads();
        }
    };

    return (
        <div className="flex flex-col h-screen w-64 bg-indigo-800 text-white p-4">
            <div className="mb-4">
                <button
                    onClick={handleNewChat}
                    className="w-full px-4 py-2 border border-white/50 rounded-md hover:bg-indigo-700 transition-colors duration-200"
                >
                    + New Chat
                </button>
            </div>
            <div className="flex-grow overflow-y-auto">
                <h2 className="text-lg font-semibold mb-2 px-2">History</h2>
                <ul className="space-y-1">
                    {/* --- CHANGE: Map over threads array and use thread object properties --- */}
                    {threads.map((thread) => (
                        <li key={thread.id}>
                            <button
                                onClick={() => setActiveThreadId(thread.id)}
                                className={`w-full text-left px-3 py-2 rounded-md truncate text-sm transition-colors duration-200 ${thread.id === activeThreadId
                                    ? 'bg-indigo-600 font-semibold'
                                    : 'hover:bg-indigo-700/50'
                                    }`}
                            >
                                {thread.title} {/* Display the title */}
                            </button>
                        </li>
                    ))}
                </ul>
            </div>
            <button
                onClick={handleDeleteAll}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-red-500/50 text-red-300 rounded-md hover:bg-red-500 hover:text-white transition-colors duration-200"
            >
                Clear All Chats
            </button>
        </div>
    );
}
