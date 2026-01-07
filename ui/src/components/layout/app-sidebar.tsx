"use client";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import { WorkspaceSwitcher } from "./workspace-switcher";
import { Workspace } from "@/types/entity";
import { ApiClient } from "@/services";
import { WorkspaceApi } from "@/services/workspace";

// 模拟数据 (实际应从 props 或 context 获取)
const user = {
  name: "User",
  email: "user@example.com",
  avatar: "/avatars/placeholder.jpg",
};

// 假设 workspaces 和 api 也是通过某种方式获取的，这里为了演示简化
// 实际使用时，AppSidebar 可能需要接收这些作为 Props
type AppSidebarProps = {
  children: React.ReactNode;
  workspaces: Workspace[];
  api: WorkspaceApi;
  isGuest?: boolean;
};

export function AppSidebar({
  children,
  workspaces,
  api,
  isGuest = false,
}: AppSidebarProps) {
  return (
    <Sidebar
      collapsible="none"
      variant="inset"
      className="h-screen overflow-hidden flex flex-col"
    >
      <SidebarHeader>
        {isGuest ? (
          <div>Guest Mode</div>
        ) : (
          <WorkspaceSwitcher workspaces={workspaces} api={api} user={user} />
        )}
      </SidebarHeader>

      <SidebarContent>{children}</SidebarContent>

      <SidebarRail />
    </Sidebar>
  );
}
