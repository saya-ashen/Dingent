import { create } from "zustand";
import type { AuthUser } from "@repo/api-client";
import Cookies from "js-cookie";

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  setAuth: (token: string, user?: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,

  accessToken: Cookies.get("access_token") || null,

  setAuth: (token, user) => {
    Cookies.set("access_token", token, { expires: 7 });
    set({ accessToken: token, user: user || null });
  },

  logout: () => {
    Cookies.remove("access_token");
    set({ accessToken: null, user: null });
  },
}));
