import type { Edge, Node } from '@xyflow/react';

export type LogItem = {
    timestamp: string;
    level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL" | string;
    message: string;
    module?: string;
    function?: string;
    context?: Record<string, unknown>;
    correlation_id?: string;
};

export type LogStats = {
    total_logs: number;
    by_level: Record<string, number>;
    by_module: Record<string, number>;
    oldest_timestamp: string | null;
    newest_timestamp: string | null;
};

export type PluginConfigItem = {
    name: string;
    type?: "string" | "integer";
    required?: boolean;
    secret?: boolean;
    description?: string;
    default?: unknown;
    value?: unknown;
};

export type PluginTool = {
    name: string;
    description?: string;
    enabled?: boolean;
};

export type AssistantPlugin = {
    // id: string;
    plugin_id: string;
    name: string;
    status?: string;
    enabled?: boolean;
    config?: PluginConfigItem[];
    tools?: PluginTool[];
};

export type Assistant = {
    id: string;
    name: string;
    description?: string;
    enabled?: boolean;
    status?: string;
    plugins?: AssistantPlugin[];
    updatedAt: string

};

export type AppSettings = {
    llm?: {
        model?: string;
        base_url?: string;
        provider?: string;
        api_key?: string;
    };
    workflows?: {
        id: string;
        name: string;
    }[]
    current_workflow?: string;
};

export type PluginManifest = {
    id: string;
    name: string;
    version?: string;
    description?: string;
    spec_version?: string;
    execution?: { mode?: string };
    dependencies?: string[];
};

// Base properties common to all nodes
interface BaseWorkflowNode {
    id: string;
    position: { x: number; y: number };
}

// Specific data and type for an Assistant node
export interface AssistantWorkflowNode extends BaseWorkflowNode {
    type: 'assistant';
    data: {
        assistantId: string;
        isStart?: boolean;
        assistantName: string;
        description?: string;
    };
}

export type DirectionRole = "forward" | "backward";

export type WorkflowNode = Node<AssistantWorkflowNode['data']>;

export type WorkflowEdge = Edge<{
    mode?: "bidirectional" | "single";
}>;

export type Workflow = {
    id: string;
    name: string;
    description?: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    created_at?: string;
    updated_at?: string;
};

// Market types
export type MarketItem = {
    id: string;
    name: string;
    description?: string;
    version?: string;
    author?: string;
    category: "plugin" | "assistant" | "workflow";
    tags?: string[];
    license?: string;
    readme?: string;
    downloads?: number;
    rating?: number;
    created_at?: string;
    updated_at?: string;
    is_installed?: boolean;
};

export type MarketMetadata = {
    version: string;
    updated_at: string;
    categories: {
        plugins: number;
        assistants: number;
        workflows: number;
    };
};

export type MarketDownloadRequest = {
    item_id: string;
    category: "plugin" | "assistant" | "workflow";
};

export type MarketDownloadResponse = {
    success: boolean;
    message: string;
    installed_path?: string;
};
