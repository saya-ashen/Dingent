import { redirect } from "next/navigation";

export default async function WorkspaceRootPage({
  params,
}: {
  params: { slug: string };
}) {
  const slug = (await params).slug || "unknown";
  redirect(`/${slug}/chat`);
}
