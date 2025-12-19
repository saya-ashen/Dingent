import { useEffect, RefObject } from "react";

export function useClickOutside(
  ref: RefObject<HTMLElement>,
  handler: () => void,
  ignoredRef?: RefObject<HTMLElement> //以此避免点击触发按钮时立刻关闭
) {
  useEffect(() => {
    const listener = (event: MouseEvent | TouchEvent) => {
      const el = ref.current;
      const ignoredEl = ignoredRef?.current;

      if (!el || el.contains(event.target as Node) || ignoredEl?.contains(event.target as Node)) {
        return;
      }
      handler();
    };

    document.addEventListener("mousedown", listener);
    document.addEventListener("touchstart", listener);
    return () => {
      document.removeEventListener("mousedown", listener);
      document.removeEventListener("touchstart", listener);
    };
  }, [ref, ignoredRef, handler]);
}
