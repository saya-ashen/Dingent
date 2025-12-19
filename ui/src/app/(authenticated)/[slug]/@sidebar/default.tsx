"use client";
import { DashboardNavSidebar } from "@/features/sidebar/DashboardNavSidebar";
import { ChatHistorySidebar } from "@/features/sidebar/ChatHistorySidebar";
import { usePathname } from 'next/navigation'

export default function SidebarSwitcher() {
  const pathname = usePathname()

  if (pathname.endsWith('/chat')) {
    return <ChatHistorySidebar />
  }

  return <DashboardNavSidebar />
}

