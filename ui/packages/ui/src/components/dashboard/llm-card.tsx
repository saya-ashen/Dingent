import type { OverviewData } from "@repo/api-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../";
import { LLMInfo } from "./components/llm-info";

interface LlmCardProps {
  llm: OverviewData["llm"];
  loading: boolean;
}

export function LlmCard({ llm, loading }: LlmCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>LLM Configuration</CardTitle>
        <CardDescription>
          Overview of the current global model configuration
        </CardDescription>
      </CardHeader>
      <CardContent>
        <LLMInfo llm={llm || {}} loading={loading} />
      </CardContent>
    </Card>
  );
}
