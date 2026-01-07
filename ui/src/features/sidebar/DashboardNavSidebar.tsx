"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings } from "lucide-react";
import { getClientApi } from "@/lib/api/client";
import { sidebarData } from "./sidebar-data";
import { AppSidebar } from "@/components/layout/app-sidebar";
import {
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import { Workspace } from "@/types/entity";

interface DashboardNavSidebarProps {
  workspaces: Workspace[];
  currentSlug: string;
  isGuest?: boolean;
}

export function DashboardNavSidebar({
  workspaces,
  currentSlug,
  isGuest = false,
}: DashboardNavSidebarProps) {
  const pathname = usePathname();

  const dynamicNavGroups = sidebarData.navGroups.map((group) => ({
    ...group,
    items: group.items.map((item) => ({
      ...item,
      url: `/${currentSlug}${item.url}`,
    })),
  }));

  return (
    <AppSidebar workspaces={workspaces} isGuest={isGuest}>
      {/* --- 区域 2: 内容区 (导航菜单) --- */}
      <SidebarContent className="px-2 scrollbar-thin scrollbar-thumb-sidebar-border scrollbar-track-transparent">
        {dynamicNavGroups.map((group) => (
          <SidebarGroup key={group.title} className="pt-4">
            {/* 统一使用 GroupLabel 样式 */}
            {group.title && (
              <SidebarGroupLabel className="px-2 text-xs font-medium text-muted-foreground/50 uppercase tracking-wider">
                {group.title}
              </SidebarGroupLabel>
            )}
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  // 简单的 isActive 判断
                  const isActive =
                    pathname === item.url ||
                    pathname.startsWith(`${item.url}/`);
                  const Icon = item.icon; // 假设 sidebarData 里存的是 Icon 组件

                  return (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton
                        asChild
                        isActive={isActive}
                        tooltip={item.title}
                        className="h-9 transition-colors"
                      >
                        <Link href={item.url}>
                          {Icon && <Icon className="mr-2 size-4" />}
                          <span className="truncate">{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      {/* --- 区域 3: 底部 (通用设置等) --- */}
      <SidebarFooter className="p-2">
        <SidebarMenu>
          <SidebarSeparator className="my-2 opacity-50" />
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <Link href={`/${currentSlug}/chat`}>
                <Settings className="size-4" />
                <span>Go To Chat</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </AppSidebar>
  );
}
