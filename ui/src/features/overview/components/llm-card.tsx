import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { LLMInfo } from "@/features/dashboard/components/llm-info";
import { OverviewData } from "@/types/entity";

interface LlmCardProps {
  llm: OverviewData["llm"];
}

export function LlmCard({ llm }: LlmCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>LLM Configuration</CardTitle>
        <CardDescription>
          Overview of the current global model configuration
        </CardDescription>
      </CardHeader>
      <CardContent>
        <LLMInfo llm={llm || {}} />
      </CardContent>
    </Card>
  );
}
