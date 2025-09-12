import { Outlet } from "@tanstack/react-router";
import { getCookie } from "@repo/lib/cookies";
import { cn } from "@repo/lib/utils";
import { LayoutProvider, SearchProvider } from "@repo/ui/providers";
import {
  SidebarInset,
  SidebarProvider,
  AppSidebar,
  SkipToMain,
} from "@repo/ui/components";

type AuthenticatedLayoutProps = {
  children?: React.ReactNode;
};

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const defaultOpen = getCookie("sidebar_state") !== "false";
  return (
    <SearchProvider>
      <LayoutProvider>
        <SidebarProvider defaultOpen={defaultOpen}>
          <SkipToMain />
          <AppSidebar />
          <SidebarInset
            className={cn(
              // Set content container, so we can use container queries
              "@container/content",

              // If layout is fixed, set the height
              // to 100svh to prevent overflow
              "has-[[data-layout=fixed]]:h-svh",

              // If layout is fixed and sidebar is inset,
              // set the height to 100svh - spacing (total margins) to prevent overflow
              "peer-data-[variant=inset]:has-[[data-layout=fixed]]:h-[calc(100svh-(var(--spacing)*4))]",
            )}
          >
            {children ?? <Outlet />}
          </SidebarInset>
        </SidebarProvider>
      </LayoutProvider>
    </SearchProvider>
  );
}
