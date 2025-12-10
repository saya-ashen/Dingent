export const dynamic = 'force-dynamic';
import { redirect } from "next/navigation";
import { api, getBaseUrl } from "@repo/api-client";
import { getCookie } from "@repo/lib/cookies";

export default async function DashboardRootPage() {
  const lastSlug = getCookie("last_workspace_slug");
  if (lastSlug) {
    redirect(`/${lastSlug}`);
  }

  console.log("workspaces", getBaseUrl());
  const workspaces = await api.dashboard.workspaces.listWorkspaces();

  if (workspaces.length > 0) {
    redirect(`/${workspaces[0]!.slug}`);
  }

  redirect("/onboarding");
}
