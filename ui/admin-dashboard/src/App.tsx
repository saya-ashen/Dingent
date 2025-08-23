import { Route, Routes } from "react-router-dom";
import { DefaultLayout } from "@/layouts/DefaultLayout";
import { WideLayout } from "@/layouts/WideLayout";
import AssistantsPage from "@/pages/Assistants";
import PluginsPage from "@/pages/Plugins";
import SettingsPage from "@/pages/Settings";
import LogsPage from "@/pages/Logs";
import WorkflowsPage from "@/pages/Workflows";

export default function App() {
    return (
        <Routes>
            <Route element={<DefaultLayout />}>
                <Route path="/" element={<AssistantsPage />} />
                <Route path="/plugins" element={<PluginsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/logs" element={<LogsPage />} />
            </Route>

            {/* 使用宽屏布局的页面 */}
            <Route element={<WideLayout />}>
                <Route path="/workflows" element={<WorkflowsPage />} />
            </Route>
        </Routes>
    );
}
