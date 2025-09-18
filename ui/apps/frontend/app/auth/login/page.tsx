"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { LoginPage } from "@repo/ui/pages"; // 从共享包中导入

export default function LoginRoute() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleLoginSuccess = () => {
    const returnTo = searchParams.get("returnTo");

    router.push(returnTo || "/");
  };

  return (
    <LoginPage onLoginSuccess={handleLoginSuccess} />
  );
}
