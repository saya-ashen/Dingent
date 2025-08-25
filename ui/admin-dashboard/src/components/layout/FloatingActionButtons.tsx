import type { ReactNode } from "react";

export function FloatingActionButtons({ children }: { children: ReactNode }) {
    return (
        <div className="fixed top-20 right-100 z-50 flex flex-col gap-4">
            {children}
        </div>
    );
}
