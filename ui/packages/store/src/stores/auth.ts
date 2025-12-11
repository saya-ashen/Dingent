import { create } from "zustand";
import type { AuthUser } from "@repo/api-client";
import Cookies from "js-cookie";


interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  // Actions
  setAuth: (token: string, user?: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,

  setAuth: (token, user) => {
    // 1. 写 Cookie (让 Next.js Server 能看到)
    Cookies.set("access_token", token, { expires: 7 });
    // 2. 更新内存状态
    set({ accessToken: token, user: user || null });
  },

  logout: () => {
    Cookies.remove("access_token");
    set({ accessToken: null, user: null });
  },
}));

