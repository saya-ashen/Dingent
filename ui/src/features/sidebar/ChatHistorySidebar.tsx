"use client";

import { useMemo } from "react";
import {
  Trash2,
  Plus,
  MessageSquare,
  Settings,
  MoreHorizontal,
  LayoutDashboard, // 替换 Settings 图标用于 Go to Dashboard
} from "lucide-react";
import { useThreadContext } from "@/providers/ThreadProvider";
import { getClientApi } from "@/lib/api/client";
import {
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
  useSidebar,
} from "@/components/ui/sidebar";
import { useWorkspaceStore } from "@/store";
import { AppSidebar } from "@/components/layout/app-sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useWorkspaceApi } from "@/hooks/use-workspace-api";

// --- 辅助函数：按时间分组 (保持不变) ---
const groupThreadsByDate = (threads: any[]) => {
  // ... (保持你原本的排序和分组逻辑) ...
  const groups: Record<string, typeof threads> = {
    Today: [],
    Yesterday: [],
    "Previous 7 Days": [],
    Older: [],
  };
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);

  const sortedThreads = [...threads].sort((a, b) => {
    const dateA = new Date(a.updatedAt || a.createdAt || 0).getTime();
    const dateB = new Date(b.updatedAt || b.createdAt || 0).getTime();
    return dateB - dateA;
  });

  sortedThreads.forEach((thread) => {
    const date = new Date(thread.updatedAt || thread.createdAt || new Date());
    if (date >= today) groups["Today"].push(thread);
    else if (date >= yesterday) groups["Yesterday"].push(thread);
    else if (date >= lastWeek) groups["Previous 7 Days"].push(thread);
    else groups["Older"].push(thread);
  });

  return Object.entries(groups).filter(([_, items]) => items.length > 0);
};

export function ChatHistorySidebar() {
  const {
    threads,
    activeThreadId,
    setActiveThreadId,
    createThread,
    deleteThread,
    deleteAllThreads,
  } = useThreadContext();
  const { isMobile, setOpenMobile } = useSidebar();
  const api = getClientApi();
  const workspaces = useWorkspaceStore((state) => state.workspaces);
  const router = useRouter();
  const pathname = usePathname();

  const groupedThreads = useMemo(() => groupThreadsByDate(threads), [threads]);

  const handleNewChat = () => {
    createThread();
    if (isMobile) setOpenMobile(false);
  };

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
    if (isMobile) setOpenMobile(false);
  };

  const { slug } = useWorkspaceApi();
  const handleDeleteAll = () => {
    if (window.confirm("Are you sure you want to delete all history?")) {
      deleteAllThreads();
    }
  };

  // Check if we're in guest mode
  const isGuestMode = pathname.includes('/guest/');

  return (
    <AppSidebar api={api.workspaces} workspaces={workspaces}>
      {/* --- 区域 1: 头部 --- */}
      <SidebarHeader className="p-4 pb-0">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              onClick={handleNewChat}
              className="h-10 border border-sidebar-border bg-sidebar shadow-sm hover:bg-sidebar-accent hover:text-sidebar-accent-foreground active:scale-[0.98] transition-all"
            >
              <Plus className="mr-2 size-4 text-muted-foreground" />
              <span className="font-medium">New Chat</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* --- 区域 2: 内容区 --- */}
      <SidebarContent className="px-2 scrollbar-thin scrollbar-thumb-sidebar-border scrollbar-track-transparent">
        {threads.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center p-4 text-center text-sm text-muted-foreground/60">
            <MessageSquare className="mb-2 size-8 opacity-20" />
            <p>No history yet</p>
          </div>
        ) : (
          groupedThreads.map(([label, groupThreads]) => (
            <SidebarGroup key={label} className="pt-4">
              <SidebarGroupLabel className="px-2 text-xs font-medium text-muted-foreground/50 uppercase tracking-wider">
                {label}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {groupThreads.map((thread: any) => (
                    <SidebarMenuItem key={thread.id}>
                      <SidebarMenuButton
                        isActive={thread.id === activeThreadId}
                        onClick={() => handleSelectThread(thread.id)}
                        className="h-9 group/item transition-colors"
                      >
                        <span className="truncate w-full text-sm">
                          {thread.title || "Untitled Chat"}
                        </span>
                      </SidebarMenuButton>

                      {/* 下拉菜单逻辑保持不变 */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <SidebarMenuAction
                            showOnHover
                            className="right-1 opacity-0 transition-opacity group-hover/item:opacity-100 data-[state=open]:opacity-100"
                          >
                            <MoreHorizontal className="size-4" />
                            <span className="sr-only">More</span>
                          </SidebarMenuAction>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          className="w-48"
                          align="start"
                          side="right"
                        >
                          <DropdownMenuItem>
                            <Settings className="mr-2 size-4 text-muted-foreground" />
                            <span>Rename</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteThread(thread.id);
                            }}
                          >
                            <Trash2 className="mr-2 size-4" />
                            <span>Delete</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))
        )}
      </SidebarContent>

      {/* --- 区域 3: 底部 --- */}
      <SidebarFooter className="p-2">
        <SidebarMenu>
          {threads.length > 0 && (
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={handleDeleteAll}
                className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
              >
                <Trash2 className="size-4" />
                <span>Clear History</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}

          {!isGuestMode && (
            <>
              <SidebarSeparator className="my-2 opacity-50" />

              <SidebarMenuItem>
                <SidebarMenuButton className="text-sidebar-foreground/80">
                  <LayoutDashboard className="size-4" />
                  <Link href={`/${slug}/overview`}>
                    <span>Go To Dashboard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </>
          )}
        </SidebarMenu>
      </SidebarFooter>
    </AppSidebar>
  );
}
