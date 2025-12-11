export const dynamic = 'force-dynamic';
import { redirect } from "next/navigation";
import { getCookie } from "@repo/lib/cookies";
import { getServerApi } from "@/lib/api/server";

export default async function DashboardRootPage() {
  const lastSlug = getCookie("last_workspace_slug");
  if (lastSlug) {
    redirect(`/${lastSlug}`);
  }
  const api = await getServerApi();

  const workspaces = await api.workspaces.list();


  if (workspaces.length > 0) {
    redirect(`/${workspaces[0]!.slug}`);
  }

  redirect("/onboarding");
}
