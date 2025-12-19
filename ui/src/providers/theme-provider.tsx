"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getCookie, setCookie, removeCookie } from "@/lib/cookies";

type Theme = "dark" | "light" | "system";
type ResolvedTheme = Exclude<Theme, "system">;

const DEFAULT_THEME = "system";
const THEME_COOKIE_NAME = "vite-ui-theme";
const THEME_COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year

type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
};

type ThemeProviderState = {
  defaultTheme: Theme;
  resolvedTheme: ResolvedTheme;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resetTheme: () => void;
};

const initialState: ThemeProviderState = {
  defaultTheme: DEFAULT_THEME,
  resolvedTheme: "light",
  theme: DEFAULT_THEME,
  setTheme: () => null,
  resetTheme: () => null,
};

const ThemeContext = createContext<ThemeProviderState>(initialState);

export function ThemeProvider({
  children,
  defaultTheme = DEFAULT_THEME,
  storageKey = THEME_COOKIE_NAME,
  ...props
}: ThemeProviderProps) {
  const [theme, _setTheme] = useState<Theme>(
    () => (getCookie(storageKey) as Theme) || defaultTheme,
  );
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme | undefined>(
    undefined,
  );
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleSystemThemeChange = () => {
      setResolvedTheme(mediaQuery.matches ? "dark" : "light");
    };

    if (theme === "system") {
      // Set the initial resolved theme
      handleSystemThemeChange();
      // Listen for changes
      mediaQuery.addEventListener("change", handleSystemThemeChange);
    } else {
      // If the theme is "light" or "dark", just set it directly.
      setResolvedTheme(theme);
    }

    // Cleanup listener on component unmount or when theme changes.
    return () => {
      mediaQuery.removeEventListener("change", handleSystemThemeChange);
    };
  }, [theme]); // Rerun this effect when the user changes the theme setting.

  useEffect(() => {
    // Wait until resolvedTheme is calculated on the client
    if (resolvedTheme) {
      const root = window.document.documentElement;
      root.classList.remove("light", "dark");
      root.classList.add(resolvedTheme);
    }
  }, [resolvedTheme]);

  const setTheme = (theme: Theme) => {
    setCookie(storageKey, theme, THEME_COOKIE_MAX_AGE);
    _setTheme(theme);
  };

  const resetTheme = () => {
    removeCookie(storageKey);
    _setTheme(DEFAULT_THEME);
  };

  const contextValue = {
    defaultTheme,
    resolvedTheme: resolvedTheme || "light",
    resetTheme,
    theme,
    setTheme,
  };

  return (
    <ThemeContext value={contextValue} {...props}>
      {children}
    </ThemeContext>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const useTheme = () => {
  const context = useContext(ThemeContext);

  if (!context) throw new Error("useTheme must be used within a ThemeProvider");

  return context;
};
