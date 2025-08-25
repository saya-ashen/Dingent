import { Outlet } from "react-router-dom";
import { Topbar } from "@/components/layout/Topbar";

export function WideLayout() {
    return (
        <div className="min-h-screen flex flex-col bg-background text-foreground">
            <Topbar />
            {/* 直接使用一个拥有更大宽度的 div 来替代 Page 组件 */}
            <main className="flex-1 w-full  mx-auto p-4">
                <Outlet />
            </main>
        </div>
    );
}
