import React, { type ReactNode } from "react";

export function FloatingActionButtons({ children }: { children: ReactNode }) {
    // Count the number of direct children passed to the component
    const childCount = React.Children.count(children);

    // Define the base classes that are always applied
    const baseClasses = "absolute top-0 z-50 flex flex-row items-center gap-2";

    // Conditionally determine the positioning class based on the number of children
    // If there is only 1 child, apply 'right-5' for more space.
    // If there are multiple children, use '-right-5' to keep them closer to the edge.
    const positionClass = childCount === 1 ? "right-5" : "-right-5";

    return (
        <div className={`${baseClasses} ${positionClass}`}>
            {children}
        </div>
    );
}
