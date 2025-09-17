import type { OverviewData } from "@repo/api-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../";
import { RecentLogs } from "./components/recent-logs";

interface RecentLogsCardProps {
  logs: OverviewData["logs"];
  loading: boolean;
}

export function RecentLogsCard({ logs, loading }: RecentLogsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Logs</CardTitle>
        <CardDescription>
          {logs?.stats?.total
            ? `Total logs: ${logs.stats.total}`
            : "Latest captured runtime logs"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <RecentLogs logs={logs?.recent || []} loading={loading} limit={8} />
      </CardContent>
    </Card>
  );
}
