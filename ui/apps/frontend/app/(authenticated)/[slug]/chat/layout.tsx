import { AuthenticatedLayout } from "@repo/ui/components";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { Providers } from "@/components/Providers";
import { getServerApi } from "@/lib/api/server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const api = await getServerApi();
  const workspaces = await api.workspaces.list();
  return (
    <Providers>
      <AuthenticatedLayout workspaces={workspaces} sidebar={<ChatHistorySidebar />}>
        {children}
      </AuthenticatedLayout>
    </Providers>
  );
}
