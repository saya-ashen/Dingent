"use client";

import * as React from "react";
import {
  Bell,
  Briefcase,
  Check,
  ChevronRight,
  CreditCard,
  Globe,
  Key,
  Link,
  Lock,
  LogOut,
  Mail,
  MessageSquare,
  Palette,
  Settings,
  Shield,
  User,
  Users,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";
import { ScrollArea } from "../ui/scroll-area";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Input } from "../ui/input";

// 模拟的设置侧边栏菜单结构
const sidebarNavItems = [
  {
    title: "Account",
    items: [
      { id: "my-account", title: "My Account", icon: User },
      { id: "preferences", title: "Preferences", icon: Settings }, // Notion 用的是 sliders，这里暂用 Settings
      { id: "notifications", title: "Notifications", icon: Bell },
      { id: "connections", title: "Connections", icon: Link },
    ],
  },
  {
    title: "Workspace",
    items: [
      { id: "general", title: "General", icon: Settings },
      { id: "people", title: "People", icon: Users }, // 这里对应你的 "People" 截图
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
  defaultTab?: string; // 允许打开时直接定位到某个 Tab（比如 "people"）
}

export function SettingsDialog({
  open,
  onOpenChange,
  defaultTab = "people",
}: SettingsDialogProps) {
  const [activeTab, setActiveTab] = React.useState(defaultTab);

  // 当 defaultTab 变化时更新 activeTab (用于外部直接打开特定设置)
  React.useEffect(() => {
    if (open) {
      setActiveTab(defaultTab);
    }
  }, [open, defaultTab]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTitle></DialogTitle>
      <DialogContent className="!max-w-none w-[90vw] h-[85vh] p-0 gap-0 overflow-hidden flex bg-background sm:rounded-xl">

        {/* === 左侧侧边栏 === */}
        <div className="w-64 bg-muted/30 border-r flex flex-col h-full">
          {/* 侧边栏头部 - 模拟 Notion 左上角的 User 区域 */}
          <div className="p-4 text-sm font-medium text-muted-foreground flex items-center gap-2">
            <div className="size-6 bg-primary/10 rounded-full flex items-center justify-center text-xs">S</div>
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
                        className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium rounded-sm transition-colors ${activeTab === item.id
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

          {/* 底部升级按钮 */}
          <div className="p-4 border-t">
            <Button variant="outline" className="w-full justify-start gap-2 text-blue-600 border-blue-200 hover:bg-blue-50">
              <span className="size-4 rounded-full border border-blue-600 flex items-center justify-center text-[10px]">↑</span>
              Upgrade Plan
            </Button>
          </div>
        </div>

        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {activeTab === 'people' ? (
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

// === 单独抽离 People 内容组件 (对应你的截图) ===
function PeopleSettingsContent() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 pt-8 pb-4">
        <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
          People
          <span className="text-muted-foreground cursor-help text-xs border rounded-full size-4 flex items-center justify-center">?</span>
        </h2>
      </div>

      <ScrollArea className="flex-1 px-8 pb-8">
        {/* 邀请链接区域 */}
        <div className="mb-8">
          <div className="text-sm font-medium mb-2">Invite link to add members</div>
          <div className="flex items-center justify-between p-3 border rounded-md bg-card">
            <div className="text-xs text-muted-foreground">
              Only people with permission to invite members can see this.
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" className="h-7 text-xs">Copy link</Button>
              <Switch defaultChecked />
            </div>
          </div>
        </div>

        {/* Tabs 区域 */}
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
              <Input placeholder="Filter by name..." className="h-8 w-[150px] lg:w-[200px]" />
              <Button size="sm" className="h-8 bg-blue-600 hover:bg-blue-700">Add members</Button>
            </div>
          </div>

          <TabsContent value="members" className="mt-0">
            {/* 模拟成员列表 */}
            <div className="space-y-1">
              <div className="flex items-center justify-between py-3 border-b border-border/50 group hover:bg-muted/30 px-2 -mx-2 rounded">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">S</div>
                  <div>
                    <div className="text-sm font-medium">Saya's Notion <span className="ml-2 text-xs text-muted-foreground">(You)</span></div>
                    <div className="text-xs text-muted-foreground">c3313433633@gmail.com</div>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">Workspace Owner</div>
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
  )
}
