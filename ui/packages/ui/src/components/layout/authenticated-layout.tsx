import { getCookie } from "@repo/lib/cookies";
import { cn } from "@repo/lib/utils";
import { LayoutProvider, SearchProvider } from "@repo/ui/providers";
import { SidebarInset, SidebarProvider, SkipToMain } from "@repo/ui/components";
import { WorkspaceInitializer } from "./workspace-initializer";
import { Workspace } from "@repo/api-client";

type AuthenticatedLayoutProps = {
  workspaces: Workspace[];
  sidebar: React.ReactNode;
  children?: React.ReactNode;
};

export function AuthenticatedLayout({ workspaces, sidebar, children }: AuthenticatedLayoutProps) {

  const defaultOpen = getCookie("sidebar_state") !== "false";

  return (
    <SearchProvider>
      <LayoutProvider>
        <WorkspaceInitializer workspaces={workspaces} />
        <SidebarProvider defaultOpen={defaultOpen}>
          <SkipToMain />

          {/* Render the sidebar that was passed in */}
          {sidebar}

          <SidebarInset
            id="main-content" // Good practice for the SkipToMain link
            className={cn(
              "@container/content",
              "has-[[data-layout=fixed]]:h-svh",
              "peer-data-[variant=inset]:has-[[data-layout=fixed]]:h-[calc(100svh-(var(--spacing)*4))]",
            )}
          >
            {children}
          </SidebarInset>
        </SidebarProvider>
      </LayoutProvider>
    </SearchProvider>
  );
}
