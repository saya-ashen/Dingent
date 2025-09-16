import { useRouter } from "next/navigation";
import { useAuthStore } from "@repo/store";
import { ConfirmDialog } from "@repo/ui/components";

interface SignOutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SignOutDialog({ open, onOpenChange }: SignOutDialogProps) {
  const router = useRouter();
  const { auth } = useAuthStore();

  const handleSignOut = () => {
    auth.reset();
    // Preserve current location for redirect after sign-in
    router.replace("/sign-in");
  };

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Sign out"
      description="Are you sure you want to sign out? You will need to sign in again to access your account."
      confirmText="Sign out"
      onConfirm={handleSignOut}
      className="sm:max-w-sm"
    />
  );
}
