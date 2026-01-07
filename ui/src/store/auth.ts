import { create } from "zustand";
import Cookies from "js-cookie";
import { AuthUser } from "@/types/entity";

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  visitorId: string | null;
  setAuth: (token: string, user?: AuthUser) => void;
  setVisitorId: (visitorId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: Cookies.get("access_token") || null,
  visitorId: Cookies.get("visitor_id") || null,

  setAuth: (token, user) => {
    Cookies.set("access_token", token, { expires: 7 });
    set({ accessToken: token, user: user || null });
  },

  setVisitorId: (visitorId: string) => {
    Cookies.set("visitor_id", visitorId);
    set({ visitorId: visitorId });
  },

  logout: () => {
    Cookies.remove("access_token");
    set({ accessToken: null, user: null });
  },
}));
