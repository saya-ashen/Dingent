import { notFound } from "next/navigation";
import { getServerApi } from "@/lib/api/server";
import { WorkspaceHydrator } from "@/components/layout/workspace-hydrator";
import Providers from "./providers";


export default async function DashboardAppLayout({
  children,
  params,
  sidebar,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
  sidebar: React.ReactNode;
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
      <Providers sidebar={sidebar}>
        <WorkspaceHydrator workspaces={workspaces} />
        {children}
      </Providers>
    </main>
  );
}


