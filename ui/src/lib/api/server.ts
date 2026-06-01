import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ApiClient } from "@/services";

const getBaseUrl = () => {
  if (process.env.API_BASE_URL) return process.env.API_BASE_URL;
  const backendUrl = process.env.BACKEND_URL || process.env.DING_BACKEND_URL;
  if (backendUrl) return backendUrl.replace(/\/$/, "") + "/api/v1";
  return "http://127.0.0.1:8000/api/v1";
};

export async function getServerApi() {
  const cookieStore = await cookies();

  return new ApiClient(
    { baseURL: getBaseUrl() },
    cookieStore.get("access_token")?.value,
    cookieStore.get("visitor_id")?.value,
    () => {
      redirect("/auth/login");
    },
  );
}
