import { notFound } from "next/navigation";
import { AuthenticatedLayout } from "@repo/ui/components";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { CopilotKitWrapper } from "@/components/CopilotKitWrapper";
import { getServerApi } from "@/lib/api/server";

interface ChatLayoutProps {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}

export default async function ChatLayout({
  children,
  params,
}: ChatLayoutProps) {
  const [api, resolvedParams] = await Promise.all([getServerApi(), params]);
  const { slug } = resolvedParams;

  const [workspaces, workspace] = await Promise.all([
    api.workspaces.list(),
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  if (!workspace) {
    notFound();
  }

  return (
    <CopilotKitWrapper>
      <AuthenticatedLayout
        workspaces={workspaces}
        sidebar={<ChatHistorySidebar />}
      >
        {children}
      </AuthenticatedLayout>
    </CopilotKitWrapper>
  );
}
