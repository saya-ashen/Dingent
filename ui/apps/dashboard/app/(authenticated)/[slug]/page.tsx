import { redirect } from "next/navigation";

export default function WorkspaceRootPage({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/${params.slug}/overview`);
}
