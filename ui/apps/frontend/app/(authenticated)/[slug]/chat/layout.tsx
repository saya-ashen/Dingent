import { notFound } from "next/navigation";

import { AuthenticatedLayout } from "@repo/ui/components";

import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { Providers } from "@/components/Providers";
import { getServerApi } from "@/lib/api/server";

/**
 * Chat layout component that provides workspace context and chat-specific UI structure.
 * Validates workspace existence and sets up the authenticated layout with chat sidebar.
 *
 * @param children - Child components to render within the layout
 * @param params - Route parameters containing the workspace slug
 * @returns The chat layout JSX element or triggers a 404 if workspace not found
 */
export default async function ChatLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  // Parallel data fetching for better performance
  const [api, { slug }] = await Promise.all([getServerApi(), params]);

  // Fetch workspaces list and validate current workspace in parallel
  // Using .catch() to handle potential API errors gracefully
  const [workspaces, workspace] = await Promise.all([
    api.workspaces.list(),
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  // Return 404 if workspace doesn't exist
  if (!workspace) {
    notFound();
  }

  return (
    <Providers>
      <AuthenticatedLayout workspaces={workspaces} sidebar={<ChatHistorySidebar />}>
        {children}
      </AuthenticatedLayout>
    </Providers>
  );
}
