"use client";
import { useState, useEffect } from "react";

const MOBILE_BREAKPOINT = 768;

export function useIsMobile() {
  // 1. Initialize state with `false`. This ensures the server render and
  // the initial client render are always the same.
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // 2. All code inside useEffect runs only on the client, after hydration.
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);

    // 3. Set the initial value on the client once it has mounted.
    setIsMobile(mql.matches);

    // 4. Define the event listener to update the state on change.
    const handleMediaQueryChange = (event: MediaQueryListEvent) => {
      setIsMobile(event.matches);
    };

    mql.addEventListener("change", handleMediaQueryChange);

    // 5. Clean up the event listener when the component unmounts.
    return () => {
      mql.removeEventListener("change", handleMediaQueryChange);
    };
  }, []); // The empty dependency array ensures this effect runs only once on mount.

  return isMobile;
}
