import { useParams } from "next/navigation";
import { useMemo } from "react";
import { getClientApi } from "@/lib/api/client";

interface UseWorkspaceApiOptions {
  visitorId?: string;
}
export function useWorkspaceApi(options?: UseWorkspaceApiOptions) {
  const params = useParams();
  const slug = params.slug as string;
  const visitorId = options?.visitorId;

  const api = useMemo(() => {
    const client = getClientApi();
    return client.forWorkspace(slug, { visitorId });
  }, [slug, visitorId]);

  const workspacesApi = useMemo(() => {
    const client = getClientApi();
    return client.workspaces;
  }, []);

  return { api, workspacesApi, slug };
}
