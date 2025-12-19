import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { OverviewLogEntry } from "@/types/entity";

export function RecentLogs({
  logs,
  loading,
  limit = 8,
}: {
  logs: OverviewLogEntry[];
  loading?: boolean;
  limit?: number;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-5 w-full" />
        ))}
      </div>
    );
  }
  if (!logs?.length) {
    return <div className="text-muted-foreground text-sm">No recent logs.</div>;
  }
  return (
    <ul className="space-y-1 text-sm">
      {logs.slice(0, limit).map((l, i) => {
        const ts = l.timestamp || l.ts || "";
        return (
          <li
            key={i}
            className="hover:bg-muted/50 flex flex-col rounded border px-2 py-1"
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "text-[10px] tracking-wide uppercase",
                  l.level === "error"
                    ? "text-red-600 dark:text-red-400"
                    : l.level === "warning"
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-muted-foreground",
                )}
              >
                {l.level || "info"}
              </span>
              <span className="text-muted-foreground text-xs">
                {ts?.replace("T", " ").replace("Z", "")}
              </span>
              {l.module && (
                <span className="text-primary/70 text-xs">{l.module}</span>
              )}
            </div>
            <div className="leading-snug">{l.message}</div>
          </li>
        );
      })}
    </ul>
  );
}
