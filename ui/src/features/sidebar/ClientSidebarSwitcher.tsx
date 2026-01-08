"use client";

import { usePathname } from "next/navigation";
import { DashboardNavSidebar } from "@/features/sidebar/DashboardNavSidebar";
import { ChatHistorySidebar } from "@/features/sidebar/ChatHistorySidebar";
import { Workspace } from "@/types/entity";

interface ClientSidebarSwitcherProps {
  workspaces: Workspace[];
  currentSlug: string;
}

export function ClientSidebarSwitcher({
  workspaces,
  currentSlug,
}: ClientSidebarSwitcherProps) {
  const pathname = usePathname();

  const isChatPage =
    pathname?.endsWith("/chat") || pathname?.includes("/chat/");

  if (isChatPage) {
    return <ChatHistorySidebar workspaces={workspaces} />;
  }

  return (
    <DashboardNavSidebar workspaces={workspaces} currentSlug={currentSlug} />
  );
}
