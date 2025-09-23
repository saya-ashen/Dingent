"use client";
import {
  AppSidebar,
  AppTitle,
  NavGroup,
} from "@repo/ui/components";
import { sidebarData } from "./data/sidebar-data";

export function DashboardNavSidebar() {
  return (
    <AppSidebar
      header={<AppTitle />}
    >
      {sidebarData.navGroups.map((props) => (
        <NavGroup key={props.title} {...props} />
      ))}
    </AppSidebar>
  );
}
