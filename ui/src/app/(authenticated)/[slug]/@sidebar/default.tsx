import { getServerApi } from "@/lib/api/server";
import { ClientSidebarSwitcher } from "@/features/sidebar/ClientSidebarSwitcher";

export default async function SidebarPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const api = await getServerApi();

  const [workspaces] = await Promise.all([api.workspaces.list()]);

  const user = {
    name: "Demo User",
    email: "demo@example.com",
    avatar: "/avatar.png",
  };

  // 2. 将数据作为 Props 传递给 Client Switcher
  return <ClientSidebarSwitcher workspaces={workspaces} currentSlug={slug} />;
}
