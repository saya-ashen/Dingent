import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Assistant, AssistantPlugin, PluginManifest } from "@/lib/types";
import {
    addPluginToAssistant,
    getAssistantsConfig,
    getAvailablePlugins,
    removePluginFromAssistant,
    saveAssistantsConfig
} from "@/lib/api";
import { safeBool, effectiveStatusForItem, toStr } from "@/lib/utils";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SearchableSelect } from "@/components/SearchableSelect";
import { PageHeader } from "@/components/layout/Page";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

export default function AssistantsPage() {
    const qc = useQueryClient();

    const assistantsQ = useQuery({
        queryKey: ["assistants"],
        queryFn: async () => (await getAssistantsConfig()) ?? [],
        staleTime: 5_000
    });

    const pluginsQ = useQuery({
        queryKey: ["available-plugins"],
        queryFn: async () => (await getAvailablePlugins()) ?? [],
        staleTime: 30_000
    });

    const [editable, setEditable] = useState<Assistant[]>([]);

    useEffect(() => {
        if (assistantsQ.data) {
            setEditable(JSON.parse(JSON.stringify(assistantsQ.data)));
        }
    }, [assistantsQ.data]);

    const saveMutation = useMutation({
        mutationFn: async (payload: Assistant[]) => {
            payload.forEach(a => {
                a.enabled = safeBool(a.enabled, false);
                a.plugins?.forEach(p => {
                    p.enabled = safeBool(p.enabled, false);
                    p.tools?.forEach(t => (t.enabled = safeBool(t.enabled, false)));
                });
            });
            await saveAssistantsConfig(payload);
        },
        onSuccess: async () => {
            toast.success("All configuration saved and refreshed successfully!");
            await qc.invalidateQueries({ queryKey: ["assistants"] });
        },
        onError: (e: any) => toast.error(e.message || "Save failed")
    });

    const addPluginMutation = useMutation({
        mutationFn: async (p: { assistantId: string; pluginName: string }) => addPluginToAssistant(p.assistantId, p.pluginName),
        onSuccess: async () => {
            toast.success("Plugin added");
            await qc.invalidateQueries({ queryKey: ["assistants"] });
        },
        onError: (e: any) => toast.error(e.message || "Add plugin failed")
    });

    const removePluginMutation = useMutation({
        mutationFn: async (p: { assistantId: string; pluginName: string }) => removePluginFromAssistant(p.assistantId, p.pluginName),
        onSuccess: async () => {
            toast.success("Plugin removed");
            await qc.invalidateQueries({ queryKey: ["assistants"] });
        },
        onError: (e: any) => toast.error(e.message || "Remove plugin failed")
    });

    return (
        <div className="space-y-4">
            <PageHeader
                title="Assistant Configuration"
                description="Manage assistants, enable/disable plugins, and edit plugin settings and tools."
                actions={
                    <Button onClick={() => saveMutation.mutate(editable)} disabled={saveMutation.isPending}>
                        {saveMutation.isPending ? "Saving..." : "Save all changes"}
                    </Button>
                }
            />

            {assistantsQ.isLoading && <LoadingSkeleton lines={5} />}
            {assistantsQ.error && <div className="text-red-600">Failed to load assistants.</div>}
            {!assistantsQ.isLoading && !assistantsQ.error && editable.length === 0 && (
                <EmptyState title="No assistants" description="There are currently no assistants to configure." />
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {editable.map((assistant, i) => (
                    <AssistantCard
                        key={assistant.id || i}
                        assistant={assistant}
                        onChange={(a) => {
                            const next = [...editable];
                            next[i] = a;
                            setEditable(next);
                        }}
                        availablePlugins={pluginsQ.data || []}
                        onAddPlugin={(pluginName) => addPluginMutation.mutate({ assistantId: assistant.id, pluginName })}
                        onRemovePlugin={(pluginName) => removePluginMutation.mutate({ assistantId: assistant.id, pluginName })}
                    />
                ))}
            </div>
        </div>
    );
}

function AssistantCard({
    assistant,
    onChange,
    availablePlugins,
    onAddPlugin,
    onRemovePlugin
}: {
    assistant: Assistant;
    onChange: (a: Assistant) => void;
    availablePlugins: PluginManifest[];
    onAddPlugin: (pluginName: string) => void;
    onRemovePlugin: (pluginName: string) => void;
}) {
    const enabled = safeBool(assistant.enabled, false);
    const { level, label } = effectiveStatusForItem(assistant.status, enabled);

    const currentNames = new Set((assistant.plugins || []).map(p => p.name));
    const addable = useMemo(() => availablePlugins.filter(p => !currentNames.has(p.name)).map(p => p.name), [availablePlugins, currentNames]);

    const [selectedAdd, setSelectedAdd] = useState<string>("");

    return (
        <div className="rounded-lg border p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="text-lg font-semibold">{assistant.name || "Unnamed"}</div>
                    <div className="mt-1 text-sm text-muted-foreground">{assistant.description || "No description"}</div>
                </div>
                <StatusBadge level={level} label={label} title={assistant.status} />
            </div>

            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="space-y-2">
                    <Label>Name</Label>
                    <Input value={assistant.name || ""} onChange={(e) => onChange({ ...assistant, name: e.target.value })} />
                </div>
                <div className="space-y-2">
                    <Label>Enable assistant</Label>
                    <div className="flex h-10 items-center">
                        <Switch checked={enabled} onCheckedChange={(v) => onChange({ ...assistant, enabled: v })} />
                    </div>
                </div>
            </div>

            <div className="mt-3 space-y-2">
                <Label>Description</Label>
                <Textarea value={assistant.description || ""} onChange={(e) => onChange({ ...assistant, description: e.target.value })} />
            </div>

            <Separator className="my-4" />

            <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold">Plugins</h3>
                <div className="flex gap-2">
                    <SearchableSelect
                        options={addable}
                        value={selectedAdd}
                        onChange={setSelectedAdd}
                        placeholder="Select plugin to add"
                        className="min-w-[220px]"
                    />
                    <Button disabled={!selectedAdd} onClick={() => selectedAdd && onAddPlugin(selectedAdd)}>
                        Add
                    </Button>
                </div>
            </div>

            {!assistant.plugins?.length && (
                <div className="mt-2 text-sm text-muted-foreground">No plugins configured.</div>
            )}

            <div className="mt-3 space-y-3">
                {(assistant.plugins || []).map((p, j) => (
                    <PluginEditor
                        key={`${p.name}-${j}`}
                        plugin={p}
                        onChange={(np) => {
                            const next = structuredClone(assistant) as Assistant;
                            next.plugins = next.plugins || [];
                            next.plugins[j] = np;
                            onChange(next);
                        }}
                        onRemove={() => onRemovePlugin(p.name)}
                    />
                ))}
            </div>
        </div>
    );
}

function PluginEditor({
    plugin,
    onChange,
    onRemove
}: {
    plugin: AssistantPlugin;
    onChange: (p: AssistantPlugin) => void;
    onRemove: () => void;
}) {
    const enabled = safeBool(plugin.enabled, false);
    const { level, label } = effectiveStatusForItem(plugin.status, enabled);

    return (
        <div className="rounded-md border p-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="font-mono">Plugin: {toStr(plugin.name)}</div>
                    <StatusBadge level={level} label={label} title={plugin.status} />
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Enable</span>
                        <Switch checked={enabled} onCheckedChange={(v) => onChange({ ...plugin, enabled: v })} />
                    </div>

                    <ConfirmDialog
                        title="Confirm Remove Plugin"
                        message={`Are you sure you want to remove plugin '${plugin.name}'?`}
                        confirmText="Confirm Remove"
                        onConfirm={onRemove}
                        trigger={<Button variant="destructive" size="icon">🗑️</Button>}
                    />
                </div>
            </div>

            {!!plugin.config?.length && (
                <div className="mt-3 space-y-2">
                    <div className="text-sm font-medium">User Configuration</div>
                    {plugin.config!.map((item, idx) => {
                        const id = `cfg_${plugin.name}_${idx}`;
                        const label = `${item.name}${item.required ? " (Required)" : ""}`;
                        const desc = item.description || `Set ${item.name}`;
                        const value = (item.value ?? item.default) as any;

                        if (item.type === "integer") {
                            const iv = Number.isFinite(Number(value)) ? Number(value) : 0;
                            return (
                                <div key={id} className="grid grid-cols-1 gap-2 md:grid-cols-[240px_1fr]">
                                    <Label htmlFor={id}>{label}</Label>
                                    <Input
                                        id={id}
                                        type="number"
                                        value={iv}
                                        onChange={(e) => {
                                            const next = structuredClone(plugin);
                                            next.config![idx].value = Number(e.target.value);
                                            onChange(next);
                                        }}
                                        placeholder={desc}
                                    />
                                </div>
                            );
                        }

                        return (
                            <div key={id} className="grid grid-cols-1 gap-2 md:grid-cols-[240px_1fr]">
                                <Label htmlFor={id}>{label}</Label>
                                <Input
                                    id={id}
                                    type={item.secret ? "password" : "text"}
                                    value={toStr(value)}
                                    onChange={(e) => {
                                        const next = structuredClone(plugin);
                                        next.config![idx].value = e.target.value;
                                        onChange(next);
                                    }}
                                    placeholder={desc}
                                />
                            </div>
                        );
                    })}
                </div>
            )}

            {!!plugin.tools?.length && (
                <div className="mt-3">
                    <div className="text-sm font-medium">Tools</div>
                    <div className="mt-2 space-y-1">
                        {plugin.tools!.map((tool, k) => (
                            <div key={k} className="flex items-center justify-between rounded border p-2">
                                <div>
                                    <div className="font-mono">{tool.name}</div>
                                    {tool.description && <div className="text-xs text-muted-foreground">{tool.description}</div>}
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-muted-foreground">Enable</span>
                                    <Switch
                                        checked={safeBool(tool.enabled, false)}
                                        onCheckedChange={(v) => {
                                            const next = structuredClone(plugin);
                                            next.tools![k].enabled = v;
                                            onChange(next);
                                        }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
