import { QueryCache, QueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { toast } from "sonner";
// 注意：重定向逻辑将从这里移出

export const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          // 你的 retry 逻辑保持不变
          if (failureCount >= 0 && process.env.NODE_ENV === "development")
            return false;
          if (failureCount > 3 && process.env.NODE_ENV === "production")
            return false;
          return !(
            error instanceof AxiosError &&
            [401, 403].includes(error.response?.status ?? 0)
          );
        },
        refetchOnWindowFocus: process.env.NODE_ENV === "production",
        staleTime: 10 * 1000, // 10s
      },
      mutations: {
        // 你的 mutations.onError 逻辑可以保持，但重定向逻辑最好移出
      },
    },
    queryCache: new QueryCache({
      onError: (error) => {
        // 这里的逻辑最好移到 Axios Interceptor 中
        // 你仍然可以在这里显示通用的 toast 通知
        if (error instanceof AxiosError) {
          if (error.response?.status === 500) {
            toast.error("Internal Server Error!");
          }
        }
      },
    }),
  });
