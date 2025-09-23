import { create } from "zustand";
import { getCookie, setCookie, removeCookie } from "@repo/lib/cookies";
import type { AuthUser } from "@repo/api-client";

const ACCESS_TOKEN_KEY = "auth_access_token";

interface AuthState {
  user: AuthUser | null;
  accessToken: string;
  // Add a flag to know when hydration is done
  hydrated: boolean;
  setUser: (user: AuthUser | null) => void;
  setAccessToken: (accessToken: string) => void;
  reset: () => void;
  // New action to hydrate the store
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: "", // Always initialize as empty
  hydrated: false, // Start as not hydrated
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
    // Check if already hydrated to prevent re-running
    if (get().hydrated) return;

    try {
      const initialToken = getCookie(ACCESS_TOKEN_KEY) || "";
      if (initialToken) {
        set({ accessToken: initialToken });
      }
    } catch (e) {
      // Could happen if cookies are disabled
      console.error("Failed to hydrate auth store:", e);
    }
    // Mark as hydrated
    set({ hydrated: true });
  },
}));

// This line is okay to keep!
// The functions themselves are stable and don't depend on the initial state.
export const { setAccessToken, setUser, reset: resetAuth } = useAuthStore.getState();
