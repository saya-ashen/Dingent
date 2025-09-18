"use client";

import React from "react";
import { v4 as uuidv4 } from "uuid";
import { Trash2, Plus } from "lucide-react";
import { useThreadContext } from "@/contexts/ThreadProvider";

import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarSeparator,
  SidebarRail,
  Button,
  useSidebar,
} from "@repo/ui/components";

// 与管理后台保持一致的用户展示组件与数据来源
import { NavUser } from "@repo/ui/components";

export function ChatHistorySidebar() {
  const { threads, activeThreadId, setActiveThreadId, deleteAllThreads } =
    useThreadContext();

  const { isMobile, setOpenMobile } = useSidebar();

  const handleNewChat = () => {
    const newId = uuidv4();
    setActiveThreadId(newId);
    if (isMobile) setOpenMobile(false);
  };

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
    if (isMobile) setOpenMobile(false);
  };

  const handleDeleteAll = () => {
    if (
      window.confirm(
        "Are you sure you want to delete all conversations? This action cannot be undone.",
      )
    ) {
      deleteAllThreads();
    }
  };
  const user = {
    name: "User",
    email: "user@example.com",
    avatar: "/avatars/placeholder.jpg", // A default avatar
  };

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader className="gap-2">
        <Button variant="outline" size="sm" onClick={handleNewChat} className="justify-start">
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </SidebarHeader>

      <SidebarContent>
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
      </SidebarContent>

      <SidebarSeparator />

      <SidebarFooter className="gap-2">
        <Button
          variant="ghost"
          className="justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={handleDeleteAll}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Clear All Chats
        </Button>
        <NavUser user={user} />
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}
