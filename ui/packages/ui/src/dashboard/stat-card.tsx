import { cn } from "@repo/lib/utils";
import {
  Skeleton,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components";

export function StatCard(props: {
  title: string;
  value: string | number;
  sub?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  error?: boolean;
  className?: string;
}) {
  const { title, value, sub, icon, loading, error, className } = props;
  return (
    <Card className={cn(className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon ? (
          <div className="text-muted-foreground flex h-4 w-4 items-center justify-center">
            {icon}
          </div>
        ) : null}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-7 w-24" />
        ) : error ? (
          <div className="text-destructive text-sm">Error</div>
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
        {sub && !loading && !error ? (
          <p className="text-muted-foreground text-xs">{sub}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
