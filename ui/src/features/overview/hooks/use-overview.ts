import { useWorkspaceApi } from "@/hooks/use-workspace-api";
import { useQuery } from "@tanstack/react-query";

export function useOverviewQuery() {
  const { api, slug } = useWorkspaceApi();

  return useQuery({
    queryKey: ["workspace-overview", slug],
    queryFn: () => api.overview.get(),
  });
}
