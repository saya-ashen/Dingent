"use client";
import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/chat");
  return null;
}
