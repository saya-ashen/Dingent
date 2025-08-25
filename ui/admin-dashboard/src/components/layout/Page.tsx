import type { ReactNode } from "react";

export function Page({ children }: { children: ReactNode }) {
    return <div className="mx-auto w-full max-w-6xl space-y-4 p-4">{children}</div>;
}

export function PageHeader({ title, description, actions }: { title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
    return (
        <div className="flex flex-col items-center text-center gap-3 md:flex-row md:justify-center md:gap-6">
            <div>
                <h1 className="text-2xl font-semibold">{title}</h1>
                {description && <p className="text-sm text-muted-foreground">{description}</p>}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    );
}
