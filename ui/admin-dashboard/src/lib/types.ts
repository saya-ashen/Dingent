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
};

export type AppSettings = {
    llm?: {
        model?: string;
        base_url?: string;
        provider?: string;
        api_key?: string;
    };
    default_assistant?: string;
};

export type PluginManifest = {
    name: string;
    version?: string;
    description?: string;
    spec_version?: string;
    execution?: { mode?: string };
    dependencies?: string[];
};

export type WorkflowNode = {
    id: string;
    type: 'assistant' | 'start';
    position: { x: number; y: number };
    data: {
        assistantId: string;
        assistantName: string;
        description?: string;
        label?: string
    };
};

export type WorkflowEdge = {
    id: string;
    source: string;
    target: string;
    type?: 'default' | 'smoothstep' | 'step';
    data?: {
        condition?: string;
        label?: string;
    };
};

export type Workflow = {
    id: string;
    name: string;
    description?: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    created_at?: string;
    updated_at?: string;
};
