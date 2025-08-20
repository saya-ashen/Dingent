import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
    const { mode, setMode } = useTheme();
    return (
        <Button
            variant="ghost"
            size="icon"
            aria-label="Toggle theme"
            onClick={() => setMode(mode === "dark" ? "light" : "dark")}
            title="Toggle theme"
        >
            {mode === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
    );
}
