"use client";

import React, { useMemo } from "react";
import {
  Trash2,
  Plus,
  MessageSquare,
  Settings,
  MoreHorizontal,
} from "lucide-react";
import { useThreadContext } from "@/providers/ThreadProvider";
import {
  AppSidebar,
  useSidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuAction,
  SidebarSeparator,
} from "@repo/ui/components";
import { useParams } from "next/navigation";
import { getClientApi } from "@/lib/api/client";
import { useWorkspaceStore } from "@repo/store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@repo/ui/components";
import { cn } from "@repo/lib/utils"; // 假设你有 classnames 工具

// --- 辅助函数：按时间分组 ---
const groupThreadsByDate = (threads: any[]) => {
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

  // --- 核心修改：先对 threads 进行倒序排序 ---
  // 创建一个副本进行排序，避免修改原数组
  const sortedThreads = [...threads].sort((a, b) => {
    const dateA = new Date(a.updatedAt || a.createdAt || 0).getTime();
    const dateB = new Date(b.updatedAt || b.createdAt || 0).getTime();
    // dateB - dateA 表示降序 (最新的数字大，排在前面)
    return dateB - dateA;
  });

  // 使用排序后的数组进行遍历
  sortedThreads.forEach((thread) => {
    const date = new Date(thread.updatedAt || thread.createdAt || new Date());

    if (date >= today) {
      groups["Today"].push(thread);
    } else if (date >= yesterday) {
      groups["Yesterday"].push(thread);
    } else if (date >= lastWeek) {
      groups["Previous 7 Days"].push(thread);
    } else {
      groups["Older"].push(thread);
    }
  });

  // 过滤掉空数组并返回
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

  // 使用 useMemo 优化分组计算，避免每次渲染都重算
  const groupedThreads = useMemo(() => groupThreadsByDate(threads), [threads]);

  const handleNewChat = () => {
    createThread();
    if (isMobile) setOpenMobile(false);
  };

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
    if (isMobile) setOpenMobile(false);
  };

  const handleDeleteAll = () => {
    if (window.confirm("Are you sure you want to delete all history?")) {
      deleteAllThreads();
    }
  };

  return (
    <AppSidebar api={api} workspaces={workspaces}>
      {/* --- 区域 1: 头部 (新建对话) --- */}
      {/* 优化：增加内边距，使按钮更独立 */}
      <SidebarHeader className="p-4 pb-0">
        <SidebarMenu>
          <SidebarMenuItem>
            {/* 优化样式：全宽、Outline 风格、阴影、更强的交互反馈 */}
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

      {/* --- 区域 2: 内容区 (历史记录) --- */}
      <SidebarContent className="px-2 scrollbar-thin scrollbar-thumb-sidebar-border scrollbar-track-transparent">
        {threads.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center p-4 text-center text-sm text-muted-foreground/60">
            <MessageSquare className="mb-2 size-8 opacity-20" />
            <p>No history yet</p>
          </div>
        ) : (
          groupedThreads.map(([label, groupThreads]) => (
            <SidebarGroup key={label} className="pt-4">
              {/* 优化：更小的分组标签 */}
              <SidebarGroupLabel className="px-2 text-xs font-medium text-muted-foreground/50">
                {label}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {groupThreads.map((thread: any) => (
                    <SidebarMenuItem key={thread.id}>
                      <SidebarMenuButton
                        isActive={thread.id === activeThreadId}
                        onClick={() => handleSelectThread(thread.id)}
                        className={cn(
                          "h-9 group/item transition-colors", // group/item 用于控制删除按钮显示
                          thread.id === activeThreadId
                            ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground shadow-sm" // 激活状态增加轻微阴影
                            : "text-muted-foreground hover:text-sidebar-foreground" // 非激活状态稍微淡一点
                        )}
                      >
                        <span className="truncate w-full text-sm">
                          {thread.title || "Untitled Chat"}
                        </span>
                      </SidebarMenuButton>

                      {/* 优化：下拉菜单仅在 Hover 时显示，且保持在最右侧 */}
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
                        <DropdownMenuContent className="w-48" align="start" side="right">
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
          {/* 只有在有历史记录时才显示删除全部，避免误触 */}
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

          <SidebarSeparator className="my-2 opacity-50" />

          <SidebarMenuItem>
            <SidebarMenuButton className="text-sidebar-foreground/80">
              <Settings className="size-4" />
              <span>Settings</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </AppSidebar>
  );
}
