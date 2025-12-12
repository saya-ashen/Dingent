import "server-only";
import { cookies } from "next/headers";
import { ApiClient } from "@repo/api-client";

const getBaseUrl = () => process.env.API_BASE_URL || "http://localhost:8000/api/v1";

export async function getServerApi() {
  const cookieStore = await cookies();

  return new ApiClient(
    { baseURL: getBaseUrl() },
    () => cookieStore.get("access_token")?.value || null,
    () => {
    }
  );
}
