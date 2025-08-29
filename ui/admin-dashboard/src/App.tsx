import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import AssistantsPage from "@/pages/Assistants";
import PluginsPage from "@/pages/Plugins";
import SettingsPage from "@/pages/Settings";
import LogsPage from "@/pages/Logs";
import WorkflowsPage from "@/pages/Workflows";
import MarketPage from "@/pages/Market";

export default function App() {
    return (
        <Routes>
            <Route element={<AppLayout variant="default" />}>
                <Route path="/" element={<AssistantsPage />} />
                <Route path="/plugins" element={<PluginsPage />} />
                <Route path="/market" element={<MarketPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/logs" element={<LogsPage />} />
            </Route>

            {/* 使用宽屏布局的页面 */}
            <Route element={<AppLayout variant="wide" />}>
                <Route path="/workflows" element={<WorkflowsPage />} />
            </Route>
        </Routes>
    );
}
