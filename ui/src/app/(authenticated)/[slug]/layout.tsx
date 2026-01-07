import { notFound } from "next/navigation";
import { getServerApi } from "@/lib/api/server";
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
  const [workspace] = await Promise.all([
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  if (!workspace) {
    return notFound();
  }

  return (
    <main>
      <Providers sidebar={sidebar}>{children}</Providers>
    </main>
  );
}
