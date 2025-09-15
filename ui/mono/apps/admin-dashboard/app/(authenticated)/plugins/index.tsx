import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { deletePlugin, getAvailablePlugins } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ConfigDrawer } from "@/components/config-drawer";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { Header } from "@/components/layout/header";
import { Main } from "@/components/layout/main";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { ProfileDropdown } from "@/components/profile-dropdown";
import { Search } from "@/components/search";
import { ThemeSwitch } from "@/components/theme-switch";

export default function Plugins() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["available-plugins"],
    queryFn: async () => (await getAvailablePlugins()) ?? [],
    staleTime: 30_000,
  });

  const delMutation = useMutation({
    mutationFn: async (id: string) => deletePlugin(id),
    onSuccess: async () => {
      toast.success("Plugin deleted");
      await qc.invalidateQueries({ queryKey: ["available-plugins"] });
    },
    onError: (e: any) => toast.error(e.message || "Delete plugin failed"),
  });

  return (
    <>
      <Header>
        <Search />
        <div className="ms-auto flex items-center gap-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Plugin Management
          </h1>
          <p className="text-muted-foreground">
            Browse, delete, and install plugins (install coming soon).
          </p>
        </div>
        {q.isLoading && <LoadingSkeleton lines={5} />}
        {q.error && (
          <div className="text-red-600">
            Unable to fetch the plugin list from the backend.
          </div>
        )}
        {q.data && q.data.length === 0 && (
          <EmptyState title="No plugins found" />
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {q.data?.map((p) => (
            <div key={p.name} className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div className="text-lg font-semibold">
                  {p.name} {p.version ? `(v${p.version})` : ""}
                </div>
                <ConfirmDialog
                  title="Confirm Delete Plugin"
                  description={`Are you sure you want to delete plugin '${p.name}'? This may affect assistants that reference this plugin.`}
                  confirmText="Confirm Delete"
                  onConfirm={() => delMutation.mutate(p.id)}
                  trigger={<Button variant="destructive">Delete</Button>}
                />
              </div>
              <div className="text-muted-foreground mt-1 text-sm">
                {p.description || "No description provided."}
              </div>
              <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                <div>
                  Spec Version: <code>{p.spec_version || "N/A"}</code>
                </div>
                <div>
                  Execution Mode: <code>{p.execution?.mode || "N/A"}</code>
                </div>
              </div>
              {!!p.dependencies?.length && (
                <div className="mt-3">
                  <div className="text-sm font-medium">Dependencies</div>
                  <pre className="bg-muted mt-1 rounded p-2 text-sm">
                    {p.dependencies.join("\n")}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="rounded-lg border p-4">
          <div className="mb-2 text-sm font-medium">
            Install New Plugin (Placeholder)
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
            <input
              className="bg-background rounded border px-3 py-2"
              placeholder="https://github.com/user/my-agent-plugin.git"
            />
            <Button disabled>Install Plugin</Button>
          </div>
          <div className="text-muted-foreground mt-2 text-sm">
            Feature coming soon.
          </div>
        </div>
      </Main>
    </>
  );
}
