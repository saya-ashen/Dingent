import type { OverviewData } from "@repo/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components";
import { PluginsMiniList } from "./components/plugins-minilist";

interface PluginsCardProps {
  plugins: OverviewData["plugins"];
  loading: boolean;
}

export function PluginsCard({ plugins, loading }: PluginsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Plugins</CardTitle>
        <CardDescription>
          {plugins
            ? `${plugins.installed_total} installed`
            : "Installed plugins"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <PluginsMiniList plugins={plugins?.list || []} loading={loading} />
      </CardContent>
    </Card>
  );
}
