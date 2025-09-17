"use client";
import { useRef } from "react";
import LoadingBar, { type LoadingBarRef } from "react-top-loading-bar";

export function NavigationProgress() {
  const ref = useRef<LoadingBarRef>(null);
  return (
    <LoadingBar
      color="var(--muted-foreground)"
      ref={ref}
      shadow={true}
      height={2}
    />
  );
}
