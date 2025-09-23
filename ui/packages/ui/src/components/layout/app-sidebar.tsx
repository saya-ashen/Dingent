"use client";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarSeparator,
} from "@repo/ui/components";
import { NavUser } from "./nav-user";




// 定义 Props，允许传入自定义的头部、内容和底部
type AppSidebarProps = {
  header?: React.ReactNode;
  children: React.ReactNode; // 主要内容
  footer?: React.ReactNode;
};

// 模拟一个 user 对象，实际应用中应该从认证状态中获取
const user = {
  name: "User",
  email: "user@example.com",
  avatar: "/avatars/placeholder.jpg", // 默认头像
};

export function AppSidebar({ header, children, footer }: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon" variant="inset">
      {/* 1. 可选的头部区域 */}
      {header && <SidebarHeader>{header}</SidebarHeader>}

      {/* 2. 主要内容区域，由使用方定义 */}
      <SidebarContent>{children}</SidebarContent>

      {/* 3. 通用的底部区域 */}
      <SidebarSeparator />
      <SidebarFooter className="gap-2">
        {/* 可选的底部操作 */}
        {footer}
        {/* 统一的用户信息展示 */}
        <NavUser user={user} />
      </SidebarFooter>

      {/* 统一的展开/折叠轨道 */}
      <SidebarRail />
    </Sidebar>
  );
}
