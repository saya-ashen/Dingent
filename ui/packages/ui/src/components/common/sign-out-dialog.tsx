import { useRouter } from "next/navigation";
import { useAuthStore } from "@repo/store";
import { ConfirmDialog } from "../";

interface SignOutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SignOutDialog({ open, onOpenChange }: SignOutDialogProps) {
  const router = useRouter();
  const { reset } = useAuthStore();

  const handleSignOut = () => {
    reset();
    // Preserve current location for redirect after sign-in
    router.replace("auth/login");
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
