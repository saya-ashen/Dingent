import { Skeleton } from "../../components";

export function LLMInfo({
  llm,
  loading,
}: {
  llm: Record<string, any>;
  loading?: boolean;
}) {
  if (loading) {
    return <Skeleton className="h-6 w-40" />;
  }
  if (!llm || Object.keys(llm).length === 0) {
    return (
      <div className="text-muted-foreground text-sm">No LLM configured.</div>
    );
  }
  const displayPairs = Object.entries(llm).slice(0, 6);
  return (
    <dl className="grid grid-cols-2 gap-2 text-sm">
      {displayPairs.map(([k, v]) => (
        <div key={k} className="flex flex-col">
          <dt className="text-muted-foreground text-xs uppercase">{k}</dt>
          <dd className="break-all">{String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
