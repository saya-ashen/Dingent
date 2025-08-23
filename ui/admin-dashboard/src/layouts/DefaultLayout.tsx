import { Outlet } from "react-router-dom"; // Outlet 用于渲染子路由
import { Topbar } from "@/components/layout/Topbar";
import { Page } from "@/components/layout/Page"; // 这是你原来的Page组件

export function DefaultLayout() {
    return (
        <div className="min-h-screen flex flex-col bg-background text-foreground">
            <Topbar />
            <Page >
                <Outlet /> {/* 子页面会在这里渲染 */}
            </Page>
        </div>
    );
}
