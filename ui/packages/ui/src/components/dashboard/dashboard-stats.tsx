import { useMemo } from "react";
import type { OverviewData } from "@repo/api-client";
import { StatCard } from "./stat-card";

interface DashboardStatsProps {
  stats: OverviewData | null;
  loading: boolean;
  error: boolean;
}

export function DashboardStats({ stats, loading, error }: DashboardStatsProps) {
  const assistants = stats?.assistants;
  const plugins = stats?.plugins;
  const workflows = stats?.workflows;
  const market = stats?.market;

  const assistantActivationRate = useMemo(() => {
    if (!assistants) return "";
    if (!assistants.total) return "0%";
    return (
      ((assistants.active / assistants.total) * 100).toFixed(0) + "% active"
    );
  }, [assistants]);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Assistants"
        value={assistants ? assistants.total : "--"}
        sub={assistantActivationRate}
        loading={loading}
        error={error}
      />
      <StatCard
        title="Active Assistants"
        value={assistants ? assistants.active : "--"}
        sub={assistants ? `${assistants.inactive} inactive` : ""}
        loading={loading}
        error={error}
      />
      <StatCard
        title="Plugins"
        value={plugins ? plugins.installed_total : "--"}
        sub={
          market
            ? market.plugin_updates > 0
              ? `${market.plugin_updates} updates available`
              : "Up to date"
            : ""
        }
        loading={loading}
        error={error}
      />
      <StatCard
        title="Workflows"
        value={workflows ? workflows.total : "--"}
        sub={
          workflows?.active_workflow_id
            ? `Active: ${workflows.active_workflow_id}`
            : "No active workflow"
        }
        loading={loading}
        error={error}
      />
    </div>
  );
}
