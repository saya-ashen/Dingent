"use client";
import { useState, useEffect, useMemo } from "react";
import { api, AnalyticsData } from "@repo/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Skeleton,
} from "../";
import { StatCard } from "./stat-card";

function useAnalytics() {
  // The type here should match what your API function returns.
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getBudget()
      .then((apiData) => {
        // 1. Set the data on success
        console.log("data", apiData);
        setData(apiData);
      })
      .catch((err) => {
        // 2. Catch any errors
        setError(err.message);
      })
      .finally(() => {
        // 3. This runs regardless of success or failure
        setLoading(false);
      });
  }, []); // The empty array ensures this effect runs only once on mount

  return { data, loading, error };
}

export function AnalyticsTab() {
  const { data, loading } = useAnalytics();

  const budgetUsage = useMemo(() => {
    if (!data || !data.total_budget) return 0;
    return (data.current_cost / data.total_budget) * 100;
  }, [data]);

  const modelCostEntries = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.model_cost);
  }, [data]);

  return (
    <div className="space-y-4">
      {/* 3. UPDATED: Summary cards now reflect available data */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Current Cost"
          value={data ? `$${data.current_cost.toFixed(5)}` : "--"}
          sub={`Total Budget: $${data?.total_budget.toFixed(2) || "N/A"}`}
          loading={loading}
        />
        <StatCard
          title="Budget Usage"
          value={data ? `${budgetUsage.toFixed(2)}%` : "--"}
          sub="Percentage of total budget used"
          loading={loading}
        />
        <StatCard
          title="Total Invocations"
          value="--"
          sub="Data not available"
          loading={loading}
        />
        <StatCard
          title="Success Rate"
          value="--"
          sub="Data not available"
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="col-span-1 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Usage Over Time</CardTitle>
              {/* 4. UPDATED: Message for unimplemented feature */}
              <CardDescription>
                Time-series data collection is not yet implemented.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex h-[300px] items-center justify-center">
              <div className="text-muted-foreground">
                Chart will be displayed here once data is available.
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="col-span-1">
          {/* 5. UPDATED: Replaced "Top Assistants" with "Cost by Model" */}
          <Card>
            <CardHeader>
              <CardTitle>Cost by Model</CardTitle>
              <CardDescription>Breakdown of costs per model.</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-4">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : (
                <ul className="space-y-2">
                  {modelCostEntries.map(([model, cost]) => (
                    <li key={model} className="flex justify-between text-sm">
                      <span>{model}</span>
                      <span className="font-mono">${cost.toFixed(5)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
