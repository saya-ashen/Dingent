"use client";
import { redirect } from "next/navigation";

export default function AdminRootPage() {
  redirect("/dashboard");
  return null;
}
