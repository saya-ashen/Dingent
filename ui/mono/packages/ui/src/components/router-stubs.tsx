// Temporary stubs to replace @tanstack/react-router components
import React from 'react';

export interface LinkProps {
  to?: string;
  href?: string;
  children: React.ReactNode;
  className?: string;
  [key: string]: any;
}

export function Link({ to, href, children, className, ...props }: LinkProps) {
  const url = to || href || '#';
  return (
    <a href={url} className={className} {...props}>
      {children}
    </a>
  );
}

export function Outlet() {
  return <div>Content will be rendered here</div>;
}