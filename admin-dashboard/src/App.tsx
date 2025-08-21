import { Route, Routes } from "react-router-dom";
import { Topbar } from "@/components/layout/Topbar";
import { Page } from "@/components/layout/Page";
import AssistantsPage from "@/pages/Assistants";
import PluginsPage from "@/pages/Plugins";
import SettingsPage from "@/pages/Settings";
import LogsPage from "@/pages/Logs";

export default function App() {
    return (
        <div className="min-h-screen bg-background text-foreground">
            <Topbar />
            <Page>
                <Routes>
                    <Route path="/" element={<AssistantsPage />} />
                    <Route path="/plugins" element={<PluginsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/logs" element={<LogsPage />} />
                </Routes>
            </Page>
        </div>
    );
}
