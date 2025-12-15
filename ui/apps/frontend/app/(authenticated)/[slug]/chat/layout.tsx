import { notFound } from "next/navigation";
import { AuthenticatedLayout } from "@repo/ui/components";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { Providers } from "@/components/Providers";
import { getServerApi } from "@/lib/api/server";

interface ChatLayoutProps {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}

export default async function ChatLayout({
  children,
  params,
}: ChatLayoutProps) {
  // 1. Resolve params and get API client
  const [api, resolvedParams] = await Promise.all([getServerApi(), params]);
  const { slug } = resolvedParams;

  // 2. Fetch data in parallel
  // 使用 catch 处理 getBySlug 可能的 404 错误
  const [workspaces, workspace] = await Promise.all([
    api.workspaces.list(),
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  // 3. Validate workspace
  if (!workspace) {
    notFound();
  }

  // 4. Render
  return (
    <Providers>
      <AuthenticatedLayout
        workspaces={workspaces}
        sidebar={<ChatHistorySidebar />}
      >
        {children}
      </AuthenticatedLayout>
    </Providers>
  );
}
