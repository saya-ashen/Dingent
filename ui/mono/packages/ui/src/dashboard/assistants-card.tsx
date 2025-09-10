import type { OverviewData } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AssistantsTable } from "./assistants-table";

interface AssistantsCardProps {
  assistants: OverviewData["assistants"];
  loading: boolean;
  error: string | null;
}

export function AssistantsCard({
  assistants,
  loading,
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
        <AssistantsTable items={assistants?.list || []} loading={loading} />
      </CardContent>
    </Card>
  );
}
