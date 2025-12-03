"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { LoginPage } from "@repo/ui/pages";

export default function LoginRoute() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleLoginSuccess = () => {
    const returnTo = searchParams.get("next");

    router.push(returnTo || "/");
  };

  return (
    <LoginPage onLoginSuccess={handleLoginSuccess} />
  );
}
