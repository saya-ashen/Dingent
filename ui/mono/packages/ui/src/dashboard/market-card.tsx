import type { OverviewData } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface MarketCardProps {
  market: OverviewData["market"];
  loading: boolean;
}

export function MarketCard({ market, loading }: MarketCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Market</CardTitle>
        <CardDescription>
          {market?.metadata?.version
            ? `Version: ${market.metadata.version}`
            : "Marketplace metadata"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {loading ? (
          <Skeleton className="h-5 w-40" />
        ) : market ? (
          <>
            <div>
              Plugin Updates:{" "}
              {market.plugin_updates > 0 ? (
                <span className="font-medium text-amber-600 dark:text-amber-400">
                  {market.plugin_updates} available
                </span>
              ) : (
                <span className="text-muted-foreground">No updates</span>
              )}
            </div>
            {market.metadata?.counts && (
              <div className="text-muted-foreground">
                Counts: {JSON.stringify(market.metadata.counts)}
              </div>
            )}
          </>
        ) : (
          <div className="text-muted-foreground">
            Could not retrieve market data
          </div>
        )}
      </CardContent>
    </Card>
  );
}
