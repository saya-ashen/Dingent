export function EmptyState({ title, description }: { title: string; description?: string }) {
    return (
        <div className="flex flex-col items-center justify-center rounded-lg border p-8 text-center">
            <div className="text-lg font-medium">{title}</div>
            {description && <div className="mt-1 text-sm text-muted-foreground">{description}</div>}
        </div>
    );
}

