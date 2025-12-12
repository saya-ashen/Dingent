"use client";

import React from "react";
import { v4 as uuidv4 } from "uuid";
import { Trash2, Plus } from "lucide-react";
import { useThreadContext } from "@/contexts/ThreadProvider";
import { Button, useSidebar, AppSidebar } from "@repo/ui/components"; // 引入 AppSidebar
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@repo/ui/components"; // 引入需要的子组件
import { useParams } from "next/navigation";
import { getClientApi } from "@/lib/api/client";
import { useWorkspaceStore } from "@repo/store";

export function ChatHistorySidebar() {
  const { threads, activeThreadId, setActiveThreadId, deleteAllThreads } = useThreadContext();
  const { isMobile, setOpenMobile } = useSidebar();
  const params = useParams();
  const api = getClientApi();
  const slug = params.slug as string;
  const workspaces = useWorkspaceStore((state) => state.workspaces);

  const handleNewChat = () => {
    setActiveThreadId(uuidv4());
    if (isMobile) setOpenMobile(false);
  };

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
    if (isMobile) setOpenMobile(false);
  };

  const handleDeleteAll = () => {
    if (window.confirm("Are you sure?")) {
      deleteAllThreads();
    }
  };

  // 定义独有的头部内容
  const headerContent = (
    <Button variant="outline" size="sm" onClick={handleNewChat} className="justify-start w-full">
      <Plus className="mr-2 h-4 w-4" />
      New Chat
    </Button>
  );

  // 定义独有的底部内容
  const footerContent = (
    <Button
      variant="ghost"
      className="justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
      onClick={handleDeleteAll}
    >
      <Trash2 className="mr-2 h-4 w-4" />
      Clear All Chats
    </Button>
  );

  return (
    <AppSidebar api={api} workspaces={workspaces} >
      {/* 这里是 children，也就是主要内容 */}
      <SidebarGroup>
        <SidebarGroupLabel>History</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {threads.map((thread: { id: string; title: string }) => (
              <SidebarMenuItem key={thread.id}>
                <SidebarMenuButton
                  isActive={thread.id === activeThreadId}
                  onClick={() => handleSelectThread(thread.id)}
                  tooltip={thread.title}
                >
                  <span className="truncate">{thread.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </AppSidebar>
  );
}
