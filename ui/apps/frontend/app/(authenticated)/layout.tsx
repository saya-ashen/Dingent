import { AuthenticatedLayout } from "@repo/ui/components";
import { ChatHistorySidebar } from "../../components/ChatHistorySidebar";
import { Providers } from "@/components/Providers";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <AuthenticatedLayout sidebar={<ChatHistorySidebar />}>
        {children}
      </AuthenticatedLayout>
    </Providers>
  );
}
