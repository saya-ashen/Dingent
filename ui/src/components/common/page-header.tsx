import { ReactNode } from "react";

interface PageHeaderProps {
  heading: string;
  description?: string;
  children?: ReactNode;
}

export function PageHeader({ heading, description, children }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between space-y-2 mb-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">{heading}</h2>
        {description && <p className="text-muted-foreground">{description}</p>}
      </div>
      <div className="flex items-center space-x-2">
        {children}
      </div>
    </div>
  );
}
