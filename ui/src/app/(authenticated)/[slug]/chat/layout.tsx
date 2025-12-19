import { notFound } from "next/navigation";
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

  const [workspace] = await Promise.all([
    api.workspaces.list(),
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  if (!workspace) {
    notFound();
  }

  return (
    <CopilotKitWrapper>
      {children}
    </CopilotKitWrapper>
  );
}
