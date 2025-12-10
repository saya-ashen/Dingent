import { notFound } from "next/navigation";
import { DashboardNavSidebar } from "../../../components/NavSidebar";
import { api } from "@repo/api-client";
import { AuthenticatedLayout } from "@repo/ui/components";
import { WorkspaceUpdater } from "./workspace-updater";

export default async function WorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  // 1. 在服务端获取当前 URL 对应的 Workspace
  // 这一步同时也充当了权限校验：如果用户不属于该 slug，API 应该报错或返回空
  let workspace;
  try {
    const { slug } = await params;
    workspace = await api.dashboard.workspaces.getBySlug(slug);
  } catch (error) {
    return notFound();
  }

  return (
    <AuthenticatedLayout sidebar={<DashboardNavSidebar />}>
      <WorkspaceUpdater workspace={workspace} />
      {children}
    </AuthenticatedLayout>
  );
}
