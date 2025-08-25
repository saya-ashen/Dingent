import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface ContextMenuState {
    id: string;
    x: number;
    y: number;
}

interface ContextMenuItem {
    key: string;
    label: string;
    danger?: boolean;
    disabled?: boolean;
    onClick: (id: string) => void;
}

interface ContextMenuProps {
    anchor: ContextMenuState;
    onDelete: (id: string) => void;
    onClose: () => void;
    items?: ContextMenuItem[];
    autoFocus?: boolean;
}

export function ContextMenu({
    anchor,
    onDelete,
    onClose,
    items,
    autoFocus = true,
}: ContextMenuProps) {
    const ref = useRef<HTMLDivElement | null>(null);
    const [pos, setPos] = useState({ top: anchor.y, left: anchor.x });

    useLayoutEffect(() => {
        const el = ref.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        let top = anchor.y;
        let left = anchor.x;
        const GAP = 4;

        if (rect.height + top > window.innerHeight) {
            top = Math.max(GAP, window.innerHeight - rect.height - GAP);
        }
        if (rect.width + left > window.innerWidth) {
            left = Math.max(GAP, window.innerWidth - rect.width - GAP);
        }
        setPos({ top, left });
    }, [anchor.x, anchor.y]);

    useEffect(() => {
        const handleDown = (e: MouseEvent) => {
            if (!ref.current) return;
            if (!ref.current.contains(e.target as Node)) {
                onClose();
            }
        };
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        window.addEventListener("mousedown", handleDown);
        window.addEventListener("keydown", handleKey);
        return () => {
            window.removeEventListener("mousedown", handleDown);
            window.removeEventListener("keydown", handleKey);
        };
    }, [onClose]);

    useEffect(() => {
        if (autoFocus) {
            ref.current?.focus();
        }
    }, [autoFocus]);

    const finalItems: ContextMenuItem[] =
        items ??
        [
            {
                key: "delete",
                label: "Delete Node",
                danger: true,
                onClick: onDelete,
            },
        ];

    const menu = (
        <div
            ref={ref}
            role="menu"
            tabIndex={-1}
            style={{
                position: "fixed",
                top: pos.top,
                left: pos.left,
                zIndex: 10000,
                minWidth: 180,
            }}
            className="rounded-md border border-border bg-popover text-popover-foreground shadow-md outline-none backdrop-blur-md"
        >
            {finalItems.map((item) => (
                <button
                    key={item.key}
                    role="menuitem"
                    disabled={item.disabled}
                    onClick={() => {
                        if (item.disabled) return;
                        item.onClick(anchor.id);
                        onClose();
                    }}
                    className={`w-full px-4 py-2 text-left text-sm flex items-center gap-2
            ${item.danger ? "text-red-600" : ""}
            ${item.disabled ? "opacity-40 cursor-not-allowed" : "hover:bg-accent hover:text-accent-foreground"}
          `}
                >
                    {item.label}
                </button>
            ))}
        </div>
    );

    return createPortal(menu, document.body);
}
