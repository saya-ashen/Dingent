import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { RecentLogs } from "@/features/dashboard/components/recent-logs";
import { OverviewData } from "@/types/entity";

interface RecentLogsCardProps {
  logs: OverviewData["logs"];
}

export function RecentLogsCard({ logs }: RecentLogsCardProps) {
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
        <RecentLogs logs={logs?.recent || []} limit={8} />
      </CardContent>
    </Card>
  );
}
