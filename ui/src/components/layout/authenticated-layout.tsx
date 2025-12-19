
type AuthenticatedLayoutProps = {
  workspaces: Workspace[];
  sidebar: React.ReactNode;
  children?: React.ReactNode;
};

export function AuthenticatedLayout({ workspaces, sidebar, children }: AuthenticatedLayoutProps) {

  const queryClient = new QueryClient();

  return (
    <QueryClientProvider client={queryClient}>
    </QueryClientProvider>
  );
}
