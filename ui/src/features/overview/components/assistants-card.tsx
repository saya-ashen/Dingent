import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { AssistantsTable } from "@/features/dashboard/components/assistants-table";
import { OverviewData } from "@/types/entity";

interface AssistantsCardProps {
  assistants: OverviewData["assistants"];
  error: string | null;
}

export function AssistantsCard({
  assistants,
  error,
}: AssistantsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Assistants</CardTitle>
        <CardDescription>
          {assistants
            ? `Total ${assistants.total}, Active ${assistants.active}, Inactive ${assistants.inactive}`
            : "Overview of assistants"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="text-destructive mb-2 text-sm">
            Failed to load: {error}
          </div>
        )}
        <AssistantsTable items={assistants?.list || []} />
      </CardContent>
    </Card>
  );
}
