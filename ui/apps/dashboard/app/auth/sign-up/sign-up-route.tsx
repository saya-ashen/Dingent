"use client";

import { SignUpPage } from "@repo/ui/pages";
import { getClientApi } from "@/lib/api/client";

export default function LoginRoute() {
  const api = getClientApi();
  return (
    <SignUpPage api={api} />
  );
}
