"use client";

import * as React from "react";
import {
  ChevronsUpDown,
  Plus,
  Settings,
  UserPlus,
  LogOut,
  Check,
} from "lucide-react";
import { useRouter, useParams, usePathname } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "../ui/sidebar";
import { Button } from "../ui/button"; // 【假设】我们需要引入 Button 组件用于顶部的两个按钮
import { CreateWorkspaceDialog } from "../common/create-workspace-dialog";
import { SettingsDialog } from "./settings-dialog";
import { WorkspaceApi } from "@/services/workspace";
import { Workspace } from "@/types/entity";

// 定义 User 类型
type UserData = {
  name: string;
  email: string;
  avatar: string;
};

interface WorkspaceSwitcherProps {
  workspaces: Workspace[];
  api: WorkspaceApi;
  user: UserData;
}

export function WorkspaceSwitcher({ workspaces, api, user }: WorkspaceSwitcherProps) {
  const params = useParams();
  const slug = params.slug as string;
  const activeWorkspace = workspaces.find((w) => w.slug === slug);
  const activeName = activeWorkspace?.name || slug || "Select Workspace";
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
  const [settingsDefaultTab, setSettingsDefaultTab] = React.useState("general");
  const openSettings = (tab = "general") => {
    setSettingsDefaultTab(tab);
    setIsSettingsOpen(true);
  };

  // 【模拟】Notion 风格的元数据，实际应从 activeWorkspace 获取
  const workspaceMeta = "测试版 · 1 位成员";

  const { isMobile } = useSidebar();
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const handleSwitch = (workspaceSlug: string) => {
    const newPath = pathname.replace(new RegExp(`^/${slug}`), `/${workspaceSlug}`);
    router.push(newPath);
  };

  // 工作区 Logo 的通用样式
  const WorkspaceLogo = ({ name, className }: { name: string; className?: string }) => (
    <div className={`bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square items-center justify-center rounded-md border ${className}`}>
      {name.charAt(0).toUpperCase()}
    </div>
  );

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <WorkspaceLogo name={activeName} className="size-8" />
              <div className="grid flex-1 text-start text-sm leading-tight">
                <span className="truncate font-semibold">{activeName}</span>
                <span className="truncate text-xs text-muted-foreground">{workspaceMeta}</span>
              </div>
              <ChevronsUpDown className="ml-auto size-4 opacity-50" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-64 rounded-lg p-0" // p-0 让内部自定义布局接管内边距
            align="start"
            side={isMobile ? "bottom" : "right"}
            sideOffset={4}
          >
            {/* Let's try to match Notion style */}

            {/* === 第一部分：当前工作区头部信息与快捷按钮 === */}
            <div className="p-2">
              <div className="flex items-center gap-2 px-1 py-1.5 mb-2">
                <WorkspaceLogo name={activeName} className="size-10 text-lg" />
                <div>
                  <div className="font-medium text-sm">{activeName}</div>
                  <div className="text-xs text-muted-foreground">{workspaceMeta}</div>
                </div>
              </div>

              {/* 两个并排的操作按钮 */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 justify-start h-8 px-2 text-xs font-normal text-muted-foreground hover:text-foreground"
                  onClick={() => openSettings("general")}
                >
                  <Settings className="mr-2 size-4" />
                  设置
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 justify-start h-8 px-2 text-xs font-normal text-muted-foreground hover:text-foreground"
                  onClick={() => openSettings("people")}
                >
                  <UserPlus className="mr-2 size-4" />
                  邀请成员
                </Button>
              </div>
            </div>

            <DropdownMenuSeparator />

            {/* === 第二部分：用户标识与工作区列表 === */}
            {/* Notion 这里用用户的邮箱作为小标题 */}
            <div className="px-3 py-1.5 text-xs text-muted-foreground font-medium">
              {user.email}
            </div>

            {workspaces.map((workspace) => {
              const isActive = workspace.slug === slug;
              return (
                <DropdownMenuItem
                  key={workspace.id}
                  onClick={() => handleSwitch(workspace.slug)}
                  className="gap-2 p-2 focus:bg-accent"
                >
                  <WorkspaceLogo name={workspace.name} className="size-6 text-xs" />
                  <span className="flex-1 truncate text-sm">{workspace.name}</span>
                  {/* 选中状态打勾 */}
                  {isActive && <Check className="ml-auto size-4 text-muted-foreground" />}
                </DropdownMenuItem>
              );
            })}

            {/* 新建工作区 - Notion 风格是蓝色文字 */}
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setIsDialogOpen(true);
              }}
              className="gap-2 p-2 text-blue-600 focus:text-blue-700 focus:bg-blue-50 dark:text-blue-400 dark:focus:bg-blue-950/50"
            >
              <div className="flex size-6 items-center justify-center">
                <Plus className="size-4" />
              </div>
              <div className="font-medium text-sm">新建工作区</div>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            {/* === 第三部分：底部操作 === */}
            {/* Notion 的底部通常是登出，或者添加其他账号 */}
            <DropdownMenuItem onClick={() => console.log("Logout")} className="gap-2 p-2 text-muted-foreground focus:text-foreground">
              <div className="flex size-6 items-center justify-center">
                <LogOut className="size-4" />
              </div>
              <span>登出</span>
            </DropdownMenuItem>

          </DropdownMenuContent>
        </DropdownMenu>
        <SettingsDialog
          open={isSettingsOpen}
          onOpenChange={setIsSettingsOpen}
          defaultTab={settingsDefaultTab}
        />

        <CreateWorkspaceDialog
          api={api}
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
        />
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
