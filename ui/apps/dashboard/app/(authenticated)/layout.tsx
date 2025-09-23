import { AuthenticatedLayout } from "@repo/ui/components";
import { DashboardNavSidebar } from "../../components/NavSidebar";

export default function DashboardAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // Pass the DashboardNavSidebar into the generic layout's `sidebar` prop
    <AuthenticatedLayout sidebar={<DashboardNavSidebar />}>
      {children}
    </AuthenticatedLayout>
  );
}
