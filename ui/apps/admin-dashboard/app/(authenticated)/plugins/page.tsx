"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { deletePlugin, getAvailablePlugins } from "@repo/api-client";

// UI Components
import {
  Button,
  ConfigDrawer,
  ConfirmDialog,
  EmptyState,
  LoadingSkeleton,
  ProfileDropdown,
  Search,
  ThemeSwitch,
  Header,
  Main,
} from "@repo/ui/components";
import { getErrorMessage } from "@repo/lib/utils";

export default function PluginsPage() {
  const queryClient = useQueryClient();

  const {
    data: plugins,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["available-plugins"],
    queryFn: async () => (await getAvailablePlugins()) ?? [],
    staleTime: 30_000, // Refetch after 30 seconds
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePlugin(id),
    onSuccess: async () => {
      toast.success("Plugin deleted successfully");
      // Invalidate the query to refetch the updated list
      await queryClient.invalidateQueries({ queryKey: ["available-plugins"] });
    },
    onError: (e: unknown) =>
      toast.error(getErrorMessage(e, "Failed to delete the plugin")),
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
            Browse and manage your installed plugins.
          </p>
        </div>

        {isLoading && <LoadingSkeleton lines={5} />}

        {error && (
          <div className="text-red-600">
            Error: Could not fetch the plugin list from the backend.
          </div>
        )}

        {plugins && plugins.length === 0 && (
          <EmptyState
            title="No Plugins Found"
            description="No plugins are currently installed."
          />
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {plugins?.map((p) => (
            <div key={p.id} className="rounded-lg border p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-grow">
                  <div className="text-lg font-semibold">
                    {p.name} {p.version ? `(v${p.version})` : ""}
                  </div>
                  <div className="text-muted-foreground mt-1 text-sm">
                    {p.description || "No description provided."}
                  </div>
                </div>
                <ConfirmDialog
                  title="Confirm Delete Plugin"
                  description={`Are you sure you want to delete the '${p.name}' plugin? This may affect assistants that reference it.`}
                  confirmText="Confirm Delete"
                  onConfirm={() => deleteMutation.mutate(p.id)}
                  trigger={
                    <Button
                      variant="destructive"
                      disabled={
                        deleteMutation.isPending &&
                        deleteMutation.variables === p.id
                      }
                    >
                      Delete
                    </Button>
                  }
                />
              </div>

              <div className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
                <div>
                  Spec Version: <code>{p.spec_version || "N/A"}</code>
                </div>
                <div>
                  Execution Mode: <code>{p.execution?.mode || "N/A"}</code>
                </div>
              </div>

              {(p.dependencies ?? []).length > 0 && (
                <div>
                  <div className="text-sm font-medium">Dependencies</div>
                  <pre className="bg-muted mt-1 rounded p-2 text-sm">
                    {p.dependencies?.join("\n")}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Placeholder for installing a new plugin */}
        <div className="rounded-lg border p-4 mt-4">
          <div className="mb-2 font-medium">Install New Plugin</div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
            <input
              className="bg-background rounded border px-3 py-2"
              placeholder="https://github.com/user/my-agent-plugin.git"
              disabled
            />
            <Button disabled>Install Plugin</Button>
          </div>
          <div className="text-muted-foreground mt-2 text-sm">
            This feature is coming soon.
          </div>
        </div>
      </Main>
    </>
  );
}
