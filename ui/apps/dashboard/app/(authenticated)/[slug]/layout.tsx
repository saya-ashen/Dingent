import { AuthenticatedLayout } from "@repo/ui/components";
import { WorkspaceUpdater } from "./workspace-updater";
import { notFound } from "next/navigation";
import { getServerApi } from "@/lib/api/server";
import { Providers } from "@/app/providers";
import { DashboardNavSidebar } from "@/components/NavSidebar";

export default async function DashboardAppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;

}) {
  const api = await getServerApi();
  let workspace;
  const workspaces = await api.workspaces.list();
  try {
    const { slug } = await params;
    workspace = await api.workspaces.getBySlug(slug);

  } catch (error) {
    return notFound();
  }
  return (
    <Providers>
      <AuthenticatedLayout workspaces={workspaces} sidebar={<DashboardNavSidebar />}>
        <WorkspaceUpdater currentWorkspace={workspace} workspaces={workspaces} />
        {children}
      </AuthenticatedLayout>
    </Providers>
  );
}

