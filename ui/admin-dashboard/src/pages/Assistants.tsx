import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Assistant, AssistantPlugin, PluginManifest } from "@/lib/types";
import { FloatingActionButtons } from "@/components/layout/FloatingActionButtons";
import {
    addPluginToAssistant,
    getAssistantsConfig,
    getAvailablePlugins,
    removePluginFromAssistant,
    saveAssistantsConfig,
    deleteAssistant,
    addAssistant,
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
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription, DialogClose } from "@/components/ui/dialog";

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

    const [addDialogOpen, setAddDialogOpen] = useState(false);
    const [saveDialogOpen, setSaveDialogOpen] = useState(false);
    const [newAssistant, setNewAssistant] = useState<{ name: string; description: string }>({ name: "", description: "" });

    const addAssistantMutation = useMutation({
        mutationFn: async ({ name, description }: { name: string; description: string }) => addAssistant(name, description),
        onSuccess: async () => {
            toast.success("Assistant added successfully!");
            await qc.invalidateQueries({ queryKey: ["assistants"] });
            setAddDialogOpen(false); // ✨ Close dialog on success
            setNewAssistant({ name: "", description: "" }); // ✨ Reset form
        },
        onError: (e: any) => toast.error(e.message || "Add assistant failed")
    });

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
            setSaveDialogOpen(false); // ✨ Close dialog on success
            await qc.invalidateQueries({ queryKey: ["assistants"] });
        },
        onError: (e: any) => toast.error(e.message || "Save failed")
    });
    const deleteAssistantMutation = useMutation({
        mutationFn: async (assistantId: string) => deleteAssistant(assistantId),
        onSuccess: async () => {
            toast.success("Assistant deleted");
            await qc.invalidateQueries({ queryKey: ["assistants"] });
        },
        onError: (e: any) => toast.error(e.message || "Delete assistant failed")
    });


    return (
        <div className="space-y-6" > {/* Increased space-y for better vertical spacing */}
            < PageHeader
                title="Assistant Configuration"
                description="Manage assistants, enable/disable plugins, and edit plugin settings and tools."
            />

            {assistantsQ.isLoading && <LoadingSkeleton lines={5} />}
            {assistantsQ.error && <div className="text-red-600">Failed to load assistants.</div>}
            {
                !assistantsQ.isLoading && !assistantsQ.error && editable.length === 0 && (
                    <EmptyState title="No assistants" description="There are currently no assistants to configure." />
                )
            }

            <Accordion type="single" collapsible className="w-full space-y-4">
                {editable.map((assistant, i) => {
                    const enabled = safeBool(assistant.enabled, false);
                    const { level, label } = effectiveStatusForItem(assistant.status, enabled);

                    return (
                        <AccordionItem value={assistant.id || `item-${i}`} key={assistant.id || i} className="rounded-lg border">
                            <AccordionTrigger className="px-4 py-3 text-lg font-semibold hover:no-underline">
                                <div className="flex w-full items-center justify-between gap-4 pr-4"> {/* Added pr-4 for spacing before delete */}
                                    <span className="truncate">{assistant.name || "Unnamed"}</span>
                                    <div className="flex-shrink-0">
                                        <StatusBadge level={level} label={label} title={assistant.status} />
                                    </div>
                                </div>
                            </AccordionTrigger>
                            <AccordionContent className="p-4 pt-0">
                                <div className="flex justify-end mb-4"> {/* Delete button inside content for better layout */}
                                    <ConfirmDialog
                                        title="Confirm Delete Assistant"
                                        message={`Are you sure you want to delete assistant '${assistant.name || "Unnamed"}'?`}
                                        confirmText="Confirm Delete"
                                        onConfirm={() => deleteAssistantMutation.mutate(assistant.id)}
                                        trigger={
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                disabled={deleteAssistantMutation.isPending && deleteAssistantMutation.variables === assistant.id}
                                            >
                                                {(deleteAssistantMutation.isPending && deleteAssistantMutation.variables === assistant.id) && (
                                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                )}
                                                Delete Assistant
                                            </Button>
                                        }
                                    />
                                </div>
                                <AssistantEditor
                                    assistant={assistant}
                                    onChange={a => {
                                        const next = [...editable];
                                        next[i] = a;
                                        setEditable(next);
                                    }}
                                    availablePlugins={pluginsQ.data || []}
                                    onAddPlugin={pluginName => addPluginMutation.mutate({ assistantId: assistant.id, pluginName })}
                                    onRemovePlugin={pluginName => removePluginMutation.mutate({ assistantId: assistant.id, pluginName })}

                                    // ✨ Add these two new props
                                    isAddingPlugin={addPluginMutation.isPending}
                                    addingPluginDetails={addPluginMutation.variables!}
                                />
                            </AccordionContent>
                        </AccordionItem>
                    );
                })}
            </Accordion>
            <FloatingActionButtons>
                {/* --- Add Assistant Dialog --- */}
                <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
                    <DialogTrigger asChild>
                        <Button variant="outline">Add Assistant</Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Add New Assistant</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="new-name">Name (Required)</Label>
                                <Input
                                    id="new-name"
                                    value={newAssistant.name}
                                    onChange={e => setNewAssistant(prev => ({ ...prev, name: e.target.value }))}
                                    placeholder="Enter assistant name"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="new-desc">Description</Label>
                                <Textarea
                                    id="new-desc"
                                    value={newAssistant.description}
                                    onChange={e => setNewAssistant(prev => ({ ...prev, description: e.target.value }))}
                                    placeholder="Enter assistant description"
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button
                                onClick={() => addAssistantMutation.mutate({ name: newAssistant.name, description: newAssistant.description })}
                                disabled={addAssistantMutation.isPending}
                            >
                                {addAssistantMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {addAssistantMutation.isPending ? "Adding..." : "Add"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
                {/* --- Save Configuration Dialog --- */}
                <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
                    <DialogTrigger asChild>
                        <Button>Save All Changes</Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Confirm Your Changes</DialogTitle>
                            <DialogDescription>
                                Are you sure you want to save all changes? This will update the
                                configuration for all assistants and reload them.
                            </DialogDescription>
                        </DialogHeader>

                        {/* The main content/body of the dialog can go here if needed,
            but for a simple confirmation, the description is enough. */}

                        <DialogFooter className="gap-2 sm:justify-end">
                            {/* 1. Cancel Button */}
                            <DialogClose asChild>
                                <Button type="button" variant="outline">
                                    Cancel
                                </Button>
                            </DialogClose>

                            {/* 2. Save/Confirm Button */}
                            <Button
                                type="button"
                                onClick={() => saveMutation.mutate(editable)}
                                disabled={saveMutation.isPending}
                            >
                                {saveMutation.isPending ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Saving...
                                    </>
                                ) : (
                                    "Confirm & Save"
                                )}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </FloatingActionButtons>
        </div >
    );
}

function AssistantEditor({
    assistant,
    onChange,
    availablePlugins,
    onAddPlugin,
    isAddingPlugin,
    addingPluginDetails,
    onRemovePlugin
}: {
    assistant: Assistant;
    onChange: (a: Assistant) => void;
    availablePlugins: PluginManifest[];
    onAddPlugin: (pluginName: string) => void;
    isAddingPlugin: boolean;
    addingPluginDetails: { assistantId: string; pluginName: string } | null;
    onRemovePlugin: (pluginName: string) => void;
}) {
    const enabled = safeBool(assistant.enabled, false);
    const currentNames = new Set((assistant.plugins || []).map(p => p.name));
    const addable = useMemo(() => availablePlugins.filter(p => !currentNames.has(p.name)).map(p => p.name), [
        availablePlugins,
        currentNames
    ]);
    const [selectedAdd, setSelectedAdd] = useState<string>("");
    const isCurrentlyAdding = isAddingPlugin && addingPluginDetails?.assistantId === assistant.id;

    return (
        <div className="space-y-6" > {/* Increased space-y for better section separation */}
            < h3 className="text-base font-semibold" > Basic Settings</h3>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="space-y-2">
                    <Label>Name</Label>
                    <Input value={assistant.name || ""} onChange={e => onChange({ ...assistant, name: e.target.value })} />
                </div>
                <div className="space-y-2">
                    <Label>Enable assistant</Label>
                    <div className="flex h-10 items-center">
                        <Switch checked={enabled} onCheckedChange={v => onChange({ ...assistant, enabled: v })} />
                    </div>
                </div>
            </div>
            <div className="space-y-2">
                <Label>Description</Label>
                <Textarea value={assistant.description || ""} onChange={e => onChange({ ...assistant, description: e.target.value })} />
            </div>

            <Separator />

            <div className="flex items-center justify-start gap-4">
                <h3 className="text-base font-semibold">Plugins</h3>
                <div className="flex gap-2">
                    <SearchableSelect
                        options={addable}
                        value={selectedAdd}
                        onChange={setSelectedAdd}
                        placeholder="Select plugin to add"
                        className="min-w-[160px] sm:min-w-[220px]"
                    />
                    <Button
                        disabled={!selectedAdd || isCurrentlyAdding}
                        onClick={() => selectedAdd && onAddPlugin(selectedAdd)}
                    >
                        {isCurrentlyAdding && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {isCurrentlyAdding ? "Adding..." : "Add"}
                    </Button>
                </div>
            </div>

            {!assistant.plugins?.length && <div className="mt-2 text-sm text-muted-foreground">No plugins configured.</div>}

            <div className="space-y-4"> {/* Adjusted space-y for plugins */}
                {(assistant.plugins || []).map((p, j) => (
                    <PluginEditor
                        key={`${p.name}-${j}`}
                        plugin={p}
                        onChange={np => {
                            const next = structuredClone(assistant) as Assistant;
                            next.plugins = next.plugins || [];
                            next.plugins[j] = np;
                            onChange(next);
                        }}
                        onRemove={() => onRemovePlugin(p.name)}
                    />
                ))}
            </div>
        </div >
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
        <div className="rounded-md border p-4"> {/* Increased padding for better readability */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="font-mono">Plugin: {toStr(plugin.name)}</div>
                    <StatusBadge level={level} label={label} title={plugin.status} />
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Enable</span>
                        <Switch checked={enabled} onCheckedChange={v => onChange({ ...plugin, enabled: v })} />
                    </div>

                    <ConfirmDialog
                        title="Confirm Remove Plugin"
                        message={`Are you sure you want to remove plugin '${plugin.name}'?`}
                        confirmText="Confirm Remove"
                        onConfirm={onRemove}
                        trigger={
                            <Button variant="destructive" size="icon">
                                🗑️
                            </Button>
                        }
                    />
                </div>
            </div>

            {!!plugin.config?.length && (
                <div className="mt-4 space-y-3"> {/* Adjusted spacing */}
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
                                        onChange={e => {
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
                                    onChange={e => {
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
                <div className="mt-4">
                    <div className="text-sm font-medium">Tools</div>
                    <div className="mt-2 space-y-2"> {/* Increased space-y for tools */}
                        {plugin.tools!.map((tool, k) => (
                            <div key={k} className="flex items-center justify-between rounded border p-3"> {/* Increased padding */}
                                <div>
                                    <div className="font-mono">{tool.name}</div>
                                    {tool.description && <div className="text-xs text-muted-foreground">{tool.description}</div>}
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-muted-foreground">Enable</span>
                                    <Switch
                                        checked={safeBool(tool.enabled, false)}
                                        onCheckedChange={v => {
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
