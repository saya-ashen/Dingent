"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuthStore } from "@/store";

import { getErrorMessage } from "@/lib/utils";
import { useWorkspaceApi } from "@/hooks/use-workspace-api";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageContainer } from "@/components/common/page-container";


export default function PluginsPage() {
  const { api: wsApi } = useWorkspaceApi();
  const queryClient = useQueryClient();
  const auth = useAuthStore();
  const isAdmin = auth.user?.role.includes('admin');

  const { data: plugins, isLoading, error } = useQuery({
    queryKey: ["available-plugins"],
    queryFn: async () => (await wsApi.plugins.list()) ?? [],
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => {
      if (!isAdmin) {
        throw new Error("You do not have permission to delete plugins.");
      }
      return wsApi.plugins.delete(id);
    },
    onSuccess: async () => {
      toast.success("Plugin deleted successfully");
      await queryClient.invalidateQueries({ queryKey: ["available-plugins"] });
    },
    onError: (e: unknown) =>
      toast.error(getErrorMessage(e, "Failed to delete the plugin")),
  });

  return (
    <PageContainer
      title="Plugin Management"
      description="Browse, manage, and install system-wide plugins."
    >

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
          <div key={p.registry_id} className="rounded-lg border p-4 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-grow">
                {/* Plugin details (共享) */}
                <div className="text-lg font-semibold">
                  {p.display_name} {p.version ? `(v${p.version})` : ""}
                </div>
                <div className="text-muted-foreground mt-1 text-sm">
                  {p.description || "No description provided."}
                </div>
              </div>

              {/* 5. 只有管理员才能看到删除按钮 */}
              {isAdmin && (
                <ConfirmDialog
                  title="Confirm Delete Plugin"
                  description={`Are you sure you want to delete the '${p.display_name}' plugin?`}
                  onConfirm={() => deleteMutation.mutate(p.registry_id)}
                  trigger={
                    <Button
                      variant="destructive"
                      disabled={deleteMutation.isPending && deleteMutation.variables === p.registry_id}
                    >
                      Delete
                    </Button>
                  }
                />
              )}
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

      {/* 6. 只有管理员才能看到“安装新插件”的表单 */}
      {isAdmin && (
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
      )}
    </ PageContainer>
  );
}
