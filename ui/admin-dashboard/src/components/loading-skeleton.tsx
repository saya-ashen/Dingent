export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
    return (
        <div className="space-y-2">
            {Array.from({ length: lines }).map((_, i) => (
                <div key={i} className="h-4 animate-pulse rounded bg-muted" />
            ))}
        </div>
    );
}

