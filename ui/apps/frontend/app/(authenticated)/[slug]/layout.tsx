import { WorkspaceUpdater } from "@/components/workspace-updater";
import { notFound } from "next/navigation";
import { getServerApi } from "@/lib/api/server";


export default async function DashboardAppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {

  const [api, { slug }] = await Promise.all([getServerApi(), params]);
  const [workspaces, workspace] = await Promise.all([
    api.workspaces.list(),
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  if (!workspace) {
    return notFound();
  }

  return (
    <main>
      <WorkspaceUpdater currentWorkspace={workspace} workspaces={workspaces} />
      {children}
    </main>
  );
}


