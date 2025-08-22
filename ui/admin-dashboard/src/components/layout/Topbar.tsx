import { NavLink } from "react-router-dom";
import { Bot } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";

export function Topbar() {
    return (
        <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
            <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-2">
                <div className="flex items-center gap-2">
                    <Bot className="text-primary" size={20} />
                    <div className="font-semibold">Admin Dashboard</div>
                </div>
                <nav className="flex items-center gap-1">
                    <NavItem to="/" end>Assistants</NavItem>
                    <NavItem to="/plugins">Plugins</NavItem>
                    <NavItem to="/settings">Settings</NavItem>
                    <NavItem to="/logs">Logs</NavItem>
                </nav>
                <div className="flex items-center gap-2">
                    <ThemeToggle />
                </div>
            </div>
        </header>
    );
}

function NavItem({ to, children, end = false }: { to: string; children: React.ReactNode; end?: boolean }) {
    return (
        <NavLink
            to={to}
            end={end}
            className={({ isActive }) =>
                [
                    "rounded-md px-3 py-1.5 text-sm",
                    isActive ? "bg-primary/10 text-primary" : "hover:bg-muted"
                ].join(" ")
            }
        >
            {children}
        </NavLink>
    );
}
