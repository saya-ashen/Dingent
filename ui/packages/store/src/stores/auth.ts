import { create } from "zustand";
import { getCookie, setCookie, removeCookie } from "@repo/lib/cookies";
import type { AuthUser } from "@repo/api-client";

const ACCESS_TOKEN_KEY = "auth_access_token";

interface AuthState {
  user: AuthUser | null;
  accessToken: string;
  hydrated: boolean;
  setUser: (user: AuthUser | null) => void;
  setAccessToken: (accessToken: string) => void;
  reset: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: "",
  hydrated: false,
  setUser: (user) => set({ user }),
  setAccessToken: (token) => {
    setCookie(ACCESS_TOKEN_KEY, token);
    set({ accessToken: token });
  },
  reset: () => {
    removeCookie(ACCESS_TOKEN_KEY);
    set({ user: null, accessToken: "" });
  },
  hydrate: () => {
    if (get().hydrated) return;

    try {
      const initialToken = getCookie(ACCESS_TOKEN_KEY) || "";
      if (initialToken) {
        set({ accessToken: initialToken });
      }
    } catch (e) {
      console.error("Failed to hydrate auth store:", e);
    }
    set({ hydrated: true });
  },
}));

export const { setAccessToken, setUser, reset: resetAuth } = useAuthStore.getState();
