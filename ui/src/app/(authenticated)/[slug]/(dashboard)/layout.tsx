import { notFound } from "next/navigation";

import { getServerApi } from "@/lib/api/server";
import { Header } from "@/components/layout/header";
import { ConfigDrawer } from "@/components/common/config-drawer";
import { Search } from "@/components/common/search";
import { ThemeSwitch } from "@/components/common/theme-switch";
import { ProfileDropdown } from "@/components/common/profile-dropdown";
import { Main } from "@/components/layout/main";


export default async function DashboardAppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const [api, { slug }] = await Promise.all([getServerApi(), params]);

  const [workspace] = await Promise.all([
    api.workspaces.list(),
    api.workspaces.getBySlug(slug).catch(() => null),
  ]);

  if (!workspace) {
    return notFound();
  }

  return (
    <>
      <Header>
        <Search />
        <div className="ms-auto flex items-center gap-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>
      <Main>
        {children}
      </Main>
    </>
  );
}

