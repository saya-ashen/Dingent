import { OverviewData } from "@/types/entity";
import { useMemo } from "react";
import { StatCard } from "./stat-card";

interface DashboardStatsProps {
  stats: OverviewData | null;
  error: boolean;
}

export function DashboardStats({ stats, error }: DashboardStatsProps) {
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
        error={error}
      />
      <StatCard
        title="Active Assistants"
        value={assistants ? assistants.active : "--"}
        sub={assistants ? `${assistants.inactive} inactive` : ""}
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
        error={error}
      />
    </div>
  );
}
