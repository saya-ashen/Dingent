"use client";
import { useAuthStore } from "@/store";
import { getBaseUrl } from "@/lib/api/client";
import { ConfirmDialog } from "./confirm-dialog";

interface SignOutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SignOutDialog({ open, onOpenChange }: SignOutDialogProps) {
  const { logout } = useAuthStore();

  const handleSignOut = () => {
    logout();
    window.location.href = `${getBaseUrl()}/auth/sso/logout`;
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
