"use client";
import { redirect } from "next/navigation";

export default function AdminRootPage() {
  // 将用户从 /admin 重定向到 /admin/dashboard
  redirect("/dashboard");
  return null;
}
