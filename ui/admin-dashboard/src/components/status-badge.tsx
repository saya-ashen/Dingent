import { twMerge } from "tailwind-merge";

type Props = {
    label: string;
    level: "ok" | "warn" | "error" | "unknown" | "disabled";
    title?: string;
    className?: string;
};

const theme = {
    ok: "text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300/50",
    warn: "text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border-amber-300/50",
    error: "text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-900/20 border-rose-300/50",
    unknown: "text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20 border-blue-300/50",
    disabled: "text-zinc-600 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 border-zinc-300/50"
};

export function StatusBadge({ label, level, title, className }: Props) {
    return (
        <span
            title={title}
            className={twMerge(
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-sm font-semibold",
                theme[level],
                className
            )}
        >
            <span className="h-2 w-2 rounded-full bg-current" />
            {label}
        </span>
    );
}
