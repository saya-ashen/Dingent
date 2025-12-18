import "server-only";
import { cookies } from "next/headers";
import { ApiClient } from "@repo/api-client";

// 获取服务端 Base URL
const getBaseUrl = () => process.env.API_BASE_URL || "http://localhost:8000/api/v1";

export async function getServerApi() {
  const cookieStore = await cookies();

  return new ApiClient(
    { baseURL: getBaseUrl() },
    () => cookieStore.get("access_token")?.value || null,
    () => {
      // 服务端 401 处理：通常不需要做什么，或者 Redirect
      // redirect('/auth/login')
    }
  );
}
