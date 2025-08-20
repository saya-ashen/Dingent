import { useEffect, useState } from "react";

export type ThemeMode = "light" | "dark";
const KEY = "DASHBOARD_THEME";

export function getInitialTheme(): ThemeMode {
    const saved = localStorage.getItem(KEY) as ThemeMode | null;
    if (saved) return saved;
    const mql = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    return mql ? "dark" : "light";
}

export function useTheme() {
    const [mode, setMode] = useState<ThemeMode>(getInitialTheme);

    useEffect(() => {
        const root = document.documentElement;
        if (mode === "dark") root.classList.add("dark");
        else root.classList.remove("dark");
        localStorage.setItem(KEY, mode);
    }, [mode]);

    return { mode, setMode };
}
