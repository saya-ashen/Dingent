import { notFound } from "next/navigation";

import { AuthenticatedLayout } from "@repo/ui/components";

import { DashboardNavSidebar } from "@/components/NavSidebar";
import { getServerApi } from "@/lib/api/server";
import { Providers } from "@/components/providers";


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
    <Providers>
      <AuthenticatedLayout workspaces={workspaces} sidebar={<DashboardNavSidebar />}>
        {children}
      </AuthenticatedLayout>
    </Providers>
  );
}

