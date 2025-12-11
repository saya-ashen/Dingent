"use client";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarSeparator,
} from "@repo/ui/components";
import { WorkspaceSwitcher } from "./workspace-switcher";

// 模拟数据 (实际应从 props 或 context 获取)
const user = {
  name: "User",
  email: "user@example.com",
  avatar: "/avatars/placeholder.jpg",
};

// 假设 workspaces 和 api 也是通过某种方式获取的，这里为了演示简化
// 实际使用时，AppSidebar 可能需要接收这些作为 Props
import { ApiClient, Workspace } from '@repo/api-client';
type AppSidebarProps = {
  children: React.ReactNode;
  workspaces: Workspace[];
  api: ApiClient;
};

export function AppSidebar({ children, workspaces, api }: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <WorkspaceSwitcher workspaces={workspaces} api={api} user={user} />
      </SidebarHeader>

      <SidebarContent>{children}</SidebarContent>


      <SidebarRail />
    </Sidebar>
  );
}
