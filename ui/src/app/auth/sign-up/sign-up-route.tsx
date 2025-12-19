"use client";

import { SignUpPage } from "@/features/auth/components/sign-up-page";
import { getClientApi } from "@/lib/api/client";

export default function LoginRoute() {
  const api = getClientApi();
  return (
    <SignUpPage api={api} />
  );
}
