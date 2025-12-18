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


  return (
    <SearchProvider>
      <LayoutProvider>
        <WorkspaceInitializer workspaces={workspaces} />
        <SidebarProvider className="h-svh overflow-hidden">
          <SkipToMain />
          {sidebar}
          <SidebarInset
            id="main-content" // Good practice for the SkipToMain link
            className={cn(
              "relative flex flex-col h-full min-h-0 overflow-hidden",
              "@container/content"
            )}
          >
            {children}
          </SidebarInset>
        </SidebarProvider>
      </LayoutProvider>
    </SearchProvider>
  );
}
