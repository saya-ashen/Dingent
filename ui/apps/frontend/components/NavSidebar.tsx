"use client";
import {
  AppSidebar,
  NavGroup, NavGroupProps,
} from "@repo/ui/components";
import { sidebarData } from "./data/sidebar-data";
import { useParams } from "next/navigation";
import { getClientApi } from "@/lib/api/client";
import { useWorkspaceStore } from "@repo/store";

export function DashboardNavSidebar() {
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi();
  const workspaces = useWorkspaceStore((state) => state.workspaces);
  const dynamicNavGroups = sidebarData.navGroups.map((group) => ({
    ...group,
    items: group.items.map((item) => ({
      ...item,
      url: `/${slug}${item.url}`,
    })),
  })) as NavGroupProps[];
  return (
    <AppSidebar
      api={api}
      workspaces={workspaces}
    >
      {dynamicNavGroups.map((props) => (
        <NavGroup key={props.title} {...props} />
      ))}
    </AppSidebar>
  );
}
