import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deletePlugin, getAvailablePlugins } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

export default function PluginsPage() {
    const qc = useQueryClient();
    const q = useQuery({
        queryKey: ["available-plugins"],
        queryFn: async () => (await getAvailablePlugins()) ?? [],
        staleTime: 30_000
    });

    const delMutation = useMutation({
        mutationFn: async (id: string) => deletePlugin(id),
        onSuccess: async () => {
            toast.success("Plugin deleted");
            await qc.invalidateQueries({ queryKey: ["available-plugins"] });
        },
        onError: (e: any) => toast.error(e.message || "Delete plugin failed")
    });

    return (
        <div className="space-y-4">
            <PageHeader title="Plugin Management" description="Browse, delete, and install plugins (install coming soon)." />

            {q.isLoading && <LoadingSkeleton lines={5} />}
            {q.error && <div className="text-red-600">Unable to fetch the plugin list from the backend.</div>}
            {q.data && q.data.length === 0 && <EmptyState title="No plugins found" />}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {q.data?.map((p) => (
                    <div key={p.name} className="rounded-lg border p-4">
                        <div className="flex items-center justify-between">
                            <div className="text-lg font-semibold">
                                {p.name} {p.version ? `(v${p.version})` : ""}
                            </div>
                            <ConfirmDialog
                                title="Confirm Delete Plugin"
                                message={`Are you sure you want to delete plugin '${p.name}'? This may affect assistants that reference this plugin.`}
                                confirmText="Confirm Delete"
                                onConfirm={() => delMutation.mutate(p.id)}
                                trigger={<Button variant="destructive">Delete</Button>}
                            />
                        </div>
                        <div className="mt-1 text-sm text-muted-foreground">
                            {p.description || "No description provided."}
                        </div>
                        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                            <div>Spec Version: <code>{p.spec_version || "N/A"}</code></div>
                            <div>Execution Mode: <code>{p.execution?.mode || "N/A"}</code></div>
                        </div>
                        {!!p.dependencies?.length && (
                            <div className="mt-3">
                                <div className="text-sm font-medium">Dependencies</div>
                                <pre className="mt-1 rounded bg-muted p-2 text-sm">{p.dependencies.join("\n")}</pre>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="rounded-lg border p-4">
                <div className="text-sm font-medium mb-2">Install New Plugin (Placeholder)</div>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
                    <input className="rounded border bg-background px-3 py-2" placeholder="https://github.com/user/my-agent-plugin.git" />
                    <Button disabled>Install Plugin</Button>
                </div>
                <div className="mt-2 text-muted-foreground text-sm">Feature coming soon.</div>
            </div>
        </div>
    );
}
