"use client";

import * as React from "react";
import {
  Bell,
  Briefcase,
  Copy,
  CreditCard,
  ExternalLink,
  Globe,
  Link,
  Lock,
  Settings,
  Shield,
  User,
  Users,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import { ScrollArea } from "../ui/scroll-area";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { useWorkspaceApi } from "@/hooks/use-workspace-api";
import { toast } from "sonner";
import { Workspace } from "@/types/entity";

// 动态导入组件
const ModelSelector = React.lazy(() =>
  import("@/components/common/model-selector").then((module) => ({
    default: module.ModelSelector,
  })),
);

const sidebarNavItems = [
  {
    title: "Account",
    items: [
      { id: "my-account", title: "My Account", icon: User },
      { id: "preferences", title: "Preferences", icon: Settings },
      { id: "notifications", title: "Notifications", icon: Bell },
      { id: "connections", title: "Connections", icon: Link },
    ],
  },
  {
    title: "Workspace",
    items: [
      { id: "general", title: "General", icon: Settings },
      { id: "people", title: "People", icon: Users },
      { id: "teamspaces", title: "Teamspaces", icon: Briefcase },
      { id: "security", title: "Security", icon: Shield },
      { id: "identity", title: "Identity", icon: Lock },
      { id: "billing", title: "Billing", icon: CreditCard },
    ],
  },
];

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: string;
  workspace: Workspace;
}

export function SettingsDialog({
  open,
  onOpenChange,
  defaultTab = "people",
  workspace,
}: SettingsDialogProps) {
  const [activeTab, setActiveTab] = React.useState(defaultTab);

  React.useEffect(() => {
    if (open) {
      setActiveTab(defaultTab);
    }
  }, [open, defaultTab]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-none w-[90vw] h-[85vh] p-0 gap-0 overflow-hidden flex bg-background sm:rounded-xl">
        <DialogTitle className="sr-only">Workspace Settings</DialogTitle>
        <DialogDescription className="sr-only">
          Manage your workspace settings, members, and preferences.
        </DialogDescription>

        {/* === 左侧侧边栏 === */}
        <div className="w-64 bg-muted/30 border-r flex flex-col h-full shrink-0">
          <div className="p-4 text-sm font-medium text-muted-foreground flex items-center gap-2">
            <div className="size-6 bg-primary/10 rounded-full flex items-center justify-center text-xs">
              S
            </div>
            <span className="truncate">user@example.com</span>
          </div>

          <ScrollArea className="flex-1 px-2">
            <div className="space-y-6 p-2">
              {sidebarNavItems.map((group) => (
                <div key={group.title}>
                  <h4 className="mb-2 px-2 text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">
                    {group.title}
                  </h4>
                  <div className="space-y-1">
                    {group.items.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => setActiveTab(item.id)}
                        className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium rounded-sm transition-colors ${
                          activeTab === item.id
                            ? "bg-muted text-foreground"
                            : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                        }`}
                      >
                        <item.icon className="size-4" />
                        {item.title}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="p-4 border-t">
            <Button
              variant="outline"
              className="w-full justify-start gap-2 text-blue-600 border-blue-200 hover:bg-blue-50"
            >
              <span className="size-4 rounded-full border border-blue-600 flex items-center justify-center text-[10px]">
                ↑
              </span>
              Upgrade Plan
            </Button>
          </div>
        </div>

        {/* === 右侧内容区 === */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {activeTab === "general" ? (
            <GeneralSettingsContent workspace={workspace} />
          ) : activeTab === "people" ? (
            <PeopleSettingsContent />
          ) : (
            <div className="p-8 flex items-center justify-center h-full text-muted-foreground">
              Content for {activeTab}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface GeneralSettingsContentProps {
  workspace: Workspace;
}

function GeneralSettingsContent({ workspace }: GeneralSettingsContentProps) {
  const { workspacesApi } = useWorkspaceApi();
  const [guestAccessEnabled, setGuestAccessEnabled] = React.useState(false);
  const [isUpdating, setIsUpdating] = React.useState(false);

  // 表单状态
  const [workspaceName, setWorkspaceName] = React.useState("");
  const [workspaceDescription, setWorkspaceDescription] = React.useState("");
  const [defaultModelConfigId, setDefaultModelConfigId] = React.useState<
    string | null
  >(null);
  const [availableModels, setAvailableModels] = React.useState<any[]>([]);

  // 初始化数据
  React.useEffect(() => {
    if (workspace) {
      setGuestAccessEnabled(workspace.allow_guest_access ?? false);
      setWorkspaceName(workspace.name);
      setWorkspaceDescription(workspace.description ?? "");
      setDefaultModelConfigId(workspace.default_model_config_id || null);

      import("@/lib/api/client").then(({ getClientApi }) => {
        getClientApi()
          .forWorkspace(workspace.slug)
          .models.list()
          .then((models) => setAvailableModels(models || []))
          .catch((err) => console.error("Failed to load models:", err));
      });
    }
  }, [workspace]);

  const guestLink = React.useMemo(() => {
    if (!workspace) return "";
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}/guest/${workspace.slug}/chat`;
  }, [workspace]);

  const handleToggleGuestAccess = async (enabled: boolean) => {
    if (!workspace || !workspacesApi) return;
    setIsUpdating(true);
    try {
      await workspacesApi.update(workspace.slug, {
        allow_guest_access: enabled,
      });
      setGuestAccessEnabled(enabled);
      toast.success(enabled ? "Guest access enabled" : "Guest access disabled");
    } catch (error) {
      console.error("Failed to update workspace:", error);
      toast.error("Failed to update workspace settings");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(guestLink);
      toast.success("Guest link copied to clipboard");
    } catch (error) {
      toast.error("Failed to copy link");
    }
  };

  // 统一的保存处理函数
  const handleSaveAllChanges = async () => {
    if (!workspace || !workspacesApi) return;
    setIsUpdating(true);

    try {
      await workspacesApi.update(workspace.slug, {
        name: workspaceName,
        description: workspaceDescription,
        default_model_config_id: defaultModelConfigId,
      });
      toast.success("Workspace updated successfully");
    } catch (error) {
      console.error("Failed to update workspace:", error);
      toast.error("Failed to update workspace");
    } finally {
      setIsUpdating(false);
    }
  };

  if (!workspace) {
    return (
      <div className="p-8 flex items-center justify-center h-full text-muted-foreground">
        No workspace selected
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 pt-8 pb-4">
        <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
          General
          <span className="text-muted-foreground cursor-help text-xs border rounded-full size-4 flex items-center justify-center">
            ?
          </span>
        </h2>
        <p className="text-sm text-muted-foreground">
          Manage your workspace settings and guest access
        </p>
      </div>

      <ScrollArea className="flex-1 px-8 pb-8">
        <div className="space-y-8 max-w-2xl">
          {/* === Basic Information === */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Basic Information</h3>
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="workspace-name">Workspace Name</Label>
                <Input
                  id="workspace-name"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="Enter workspace name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="workspace-description">Description</Label>
                <Input
                  id="workspace-description"
                  value={workspaceDescription}
                  onChange={(e) => setWorkspaceDescription(e.target.value)}
                  placeholder="Enter workspace description (optional)"
                />
              </div>
              {/* 删除了此处多余的 Save 按钮 */}
            </div>
          </div>

          {/* === Default Model Configuration === */}
          <div className="space-y-4 pt-6 border-t">
            <h3 className="text-sm font-semibold">
              Default Model Configuration
            </h3>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Set a default LLM model for this workspace. This will be used by
                workflows and assistants that don't specify their own model.
              </p>
              <div className="space-y-2">
                <Label htmlFor="default-model">Default Model</Label>
                <React.Suspense
                  fallback={
                    <div className="h-10 bg-muted animate-pulse rounded" />
                  }
                >
                  {availableModels.length > 0 ? (
                    <ModelSelector
                      models={availableModels}
                      value={defaultModelConfigId}
                      onChange={(val: any) => {
                        setDefaultModelConfigId(val || null);
                      }}
                      placeholder="Use environment default"
                      allowClear={true}
                    />
                  ) : (
                    <div className="text-sm text-muted-foreground">
                      No models configured.{" "}
                      <a
                        href={`/${workspace.slug}/models`}
                        className="text-primary underline"
                      >
                        Configure models
                      </a>{" "}
                      first.
                    </div>
                  )}
                </React.Suspense>
              </div>
            </div>
          </div>

          {/* === Global Save Button (放置在所有表单下方) === */}
          <div className="pt-6">
            <Button
              onClick={handleSaveAllChanges}
              disabled={isUpdating}
              size="sm"
            >
              Save All Changes
            </Button>
          </div>

          {/* === Guest Access Section === */}
          <div className="space-y-4 pt-6 border-t">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  <Globe className="size-4" />
                  Guest Access
                </h3>
                <p className="text-sm text-muted-foreground">
                  Allow visitors to access your workspace without signing in
                </p>
              </div>
              <Switch
                checked={guestAccessEnabled}
                onCheckedChange={handleToggleGuestAccess}
                disabled={isUpdating}
              />
            </div>

            {guestAccessEnabled && (
              <div className="space-y-3 pl-6 pt-2">
                <div className="p-4 border rounded-lg bg-muted/30 space-y-3">
                  <div className="flex items-center gap-2">
                    <ExternalLink className="size-4 text-muted-foreground" />
                    <span className="text-sm font-medium">
                      Shareable Guest Link
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      value={guestLink}
                      readOnly
                      className="font-mono text-xs flex-1"
                      aria-label="Shareable guest link"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopyLink}
                      className="shrink-0"
                    >
                      <Copy className="size-4 mr-1" />
                      Copy
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Share this link with anyone you want to grant guest access.
                  </p>
                </div>

                <div className="p-3 border rounded-md bg-blue-50 dark:bg-blue-950/20 text-sm">
                  <div className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                    Security Note
                  </div>
                  <p className="text-blue-800 dark:text-blue-200 text-xs">
                    Guest conversations are isolated and guests cannot access
                    other users data.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

// PeopleSettingsContent 保持不变
function PeopleSettingsContent() {
  return (
    <div className="flex flex-col h-full">
      <div className="px-8 pt-8 pb-4">
        <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
          People
          <span className="text-muted-foreground cursor-help text-xs border rounded-full size-4 flex items-center justify-center">
            ?
          </span>
        </h2>
      </div>

      <ScrollArea className="flex-1 px-8 pb-8">
        <div className="mb-8">
          <div className="text-sm font-medium mb-2">
            Invite link to add members
          </div>
          <div className="flex items-center justify-between p-3 border rounded-md bg-card">
            <div className="text-xs text-muted-foreground">
              Only people with permission to invite members can see this.
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" className="h-7 text-xs">
                Copy link
              </Button>
              <Switch defaultChecked />
            </div>
          </div>
        </div>

        <Tabs defaultValue="members" className="w-full">
          <div className="flex items-center justify-between mb-4 border-b">
            <TabsList className="h-auto p-0 bg-transparent gap-6">
              <TabsTrigger
                value="guests"
                className="px-0 py-2 rounded-none bg-transparent border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none font-normal"
              >
                Guests
              </TabsTrigger>
              <TabsTrigger
                value="members"
                className="px-0 py-2 rounded-none bg-transparent border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none font-normal"
              >
                Members <span className="ml-1 text-muted-foreground">1</span>
              </TabsTrigger>
              <TabsTrigger
                value="groups"
                className="px-0 py-2 rounded-none bg-transparent border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none font-normal"
              >
                Groups
              </TabsTrigger>
            </TabsList>

            <div className="flex items-center gap-2 py-2">
              <Input
                placeholder="Filter by name..."
                className="h-8 w-[150px] lg:w-[200px]"
              />
              <Button size="sm" className="h-8 bg-blue-600 hover:bg-blue-700">
                Add members
              </Button>
            </div>
          </div>

          <TabsContent value="members" className="mt-0">
            <div className="space-y-1">
              <div className="flex items-center justify-between py-3 border-b border-border/50 group hover:bg-muted/30 px-2 -mx-2 rounded">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">
                    S
                  </div>
                  <div>
                    <div className="text-sm font-medium">
                      Saya's Notion{" "}
                      <span className="ml-2 text-xs text-muted-foreground">
                        (You)
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      c3313433633@gmail.com
                    </div>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  Workspace Owner
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="guests" className="mt-10 text-center">
            <div className="flex flex-col items-center justify-center text-muted-foreground">
              <Users className="size-10 mb-3 opacity-20" />
              <p className="text-sm">No guests yet</p>
            </div>
          </TabsContent>
        </Tabs>
      </ScrollArea>
    </div>
  );
}
