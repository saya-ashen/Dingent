import { Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { Topbar } from "@/components/layout/Topbar";

export function PageHeader({
    title,
    description,
    actions,
}: {
    title: ReactNode;
    description?: ReactNode;
    actions?: ReactNode;
}) {
    return (
        <div className="flex flex-col items-center gap-3 text-center md:flex-row md:justify-center md:gap-6">
            <div>
                <h1 className="text-2xl font-semibold">{title}</h1>
                {description && <p className="text-sm text-muted-foreground">{description}</p>}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    );
}

type AppLayoutProps = {
    variant?: "default" | "wide";
};

export function AppLayout({ variant = "default" }: AppLayoutProps) {
    const isWide = variant === "wide";

    return (
        <div className="min-h-screen flex flex-col bg-background text-foreground">
            <Topbar />
            {/* The main content area now handles its own styling based on the variant prop */}
            <main
                className={`
          flex-1 w-full mx-auto p-4
          ${isWide ? "" : "max-w-6xl space-y-4"}
        `}
            >
                <Outlet /> {/* Child pages will render here */}
            </main>
        </div>
    );
}
