import { getCookie } from "@repo/lib/cookies";
import { cn } from "@repo/lib/utils";
import { LayoutProvider, SearchProvider } from "@repo/ui/providers";
import { SidebarInset, SidebarProvider, SkipToMain } from "@repo/ui/components";
import { useAuthInterceptor } from "@repo/store";

type AuthenticatedLayoutProps = {
  // The specific sidebar component will be passed in from the app
  sidebar: React.ReactNode;
  children?: React.ReactNode;
};

export function AuthenticatedLayout({ sidebar, children }: AuthenticatedLayoutProps) {
  // Logic to read cookie remains the same
  useAuthInterceptor();

  const defaultOpen = getCookie("sidebar_state") !== "false";

  return (
    <SearchProvider>
      <LayoutProvider>
        {/* The SidebarProvider now wraps the specific sidebar and the page content */}
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
