// Temporary types to replace @tanstack/react-router types
export interface LinkProps {
  to?: string;
  href?: string;
  children: React.ReactNode;
  className?: string;
  [key: string]: any;
}