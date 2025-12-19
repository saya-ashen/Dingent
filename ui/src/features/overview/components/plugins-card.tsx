import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { PluginsMiniList } from "@/features/dashboard/components/plugins-minilist";
import { OverviewData } from "@/types/entity";

interface PluginsCardProps {
  plugins: OverviewData["plugins"];
}

export function PluginsCard({ plugins }: PluginsCardProps) {
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
        <PluginsMiniList plugins={plugins?.list || []} />
      </CardContent>
    </Card>
  );
}
