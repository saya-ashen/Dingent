import { AlertTriangle } from "lucide-react";
import { Button } from "../ui/button";

interface ErrorDisplayProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorDisplay({
  title = "Something went wrong",
  message = "There was an issue retrieving your data.",
  onRetry
}: ErrorDisplayProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center h-[400px]">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
        <AlertTriangle className="h-5 w-5 text-red-600" />
      </div>
      <h2 className="mt-4 text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} className="mt-4" variant="outline">
          Try Again
        </Button>
      )}
    </div>
  );
}
