import "server-only";
import { cookies } from "next/headers";
import { ApiClient } from "@/services";

const getBaseUrl = () =>
  process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export async function getServerApi() {
  const cookieStore = await cookies();

  return new ApiClient(
    { baseURL: getBaseUrl() },
    cookieStore.get("access_token")?.value,
    cookieStore.get("visitor_id")?.value,
    () => {},
  );
}
