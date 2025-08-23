import React from 'react';

type WidgetCardProps = {
  children: React.ReactNode;
  className?: string;
  // 如果你需要卡片顶部标题，可以传 title；不需要就不传
  title?: string;
};

export function WidgetCard({ children, className = '', title }: WidgetCardProps) {
  return (
    <div
      className={[
        // 尺寸与布局
        'w-full max-w-3xl',
        // 外观
        'rounded-xl border border-zinc-200/80 dark:border-zinc-800/80',
        'bg-white/70 dark:bg-zinc-900/60 backdrop-blur',
        'shadow-sm hover:shadow-md transition-shadow',
        // 合并外部 className
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
