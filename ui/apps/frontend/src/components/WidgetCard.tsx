import React from 'react';

type WidgetCardProps = {
    children: React.ReactNode;
    className?: string;
    title?: string;
};

export function WidgetCard({ children, className = '', title }: WidgetCardProps) {
    return (
        <div
            className={[
                'w-full max-w-7xl',
                'rounded-xl border border-zinc-200/80 dark:border-zinc-800/80',
                'bg-white/70 dark:bg-zinc-900/60 backdrop-blur',
                'shadow-sm hover:shadow-md transition-shadow',
                className,
            ].join(' ')}
        >
            {title ? (
                <div className="px-4 py-3 border-b border-zinc-200/70 dark:border-zinc-800/70">
                    <h3 className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{title}</h3>
                </div>
            ) : null}
            <div className="p-4 md:p-6">
                {children}
            </div>
        </div>
    );
}
