import { useParams } from "next/navigation";
import { useMemo } from "react";
import { getClientApi } from "@/lib/api/client";

export function useWorkspaceApi() {
  const params = useParams();
  const slug = params.slug as string;

  const api = useMemo(() => {
    const client = getClientApi();
    return client.forWorkspace(slug);
  }, [slug]);

  const workspacesApi = useMemo(() => {
    const client = getClientApi();
    return client.workspaces;
  }, []);

  return { api, workspacesApi, slug };
}
