import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";
import { WorkspaceSwitcher } from "./workspace-switcher";
import { Workspace } from "@/types/entity";
import { WorkspaceApi } from "@/services/workspace";

// 模拟数据 (实际应从 props 或 context 获取)
const user = {
  name: "User",
  email: "user@example.com",
  avatar: "/avatars/placeholder.jpg",
};

type AppSidebarProps = {
  children: React.ReactNode;
  workspaces: Workspace[];
  isGuest?: boolean;
};

export function AppSidebar({
  children,
  workspaces,
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
          <div></div>
        ) : (
          <WorkspaceSwitcher workspaces={workspaces} user={user} />
        )}
      </SidebarHeader>

      <SidebarContent>{children}</SidebarContent>

      <SidebarRail />
    </Sidebar>
  );
}
