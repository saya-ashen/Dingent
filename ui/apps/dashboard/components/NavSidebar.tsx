"use client";
import {
  AppSidebar,
  WorkspaceSwitcher,
  NavGroup, NavGroupProps,
} from "@repo/ui/components";
import { sidebarData } from "./data/sidebar-data";
import { useParams } from "next/navigation";

export function DashboardNavSidebar() {
  const params = useParams();
  const slug = params.slug as string;
  const dynamicNavGroups = sidebarData.navGroups.map((group) => ({
    ...group,
    items: group.items.map((item) => ({
      ...item,
      url: `/${slug}${item.url}`,
    })),
  })) as NavGroupProps[];
  return (
    <AppSidebar
      header={<WorkspaceSwitcher />}
    >
      {dynamicNavGroups.map((props) => (
        <NavGroup key={props.title} {...props} />
      ))}
    </AppSidebar>
  );
}
