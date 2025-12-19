"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getCookie, setCookie } from "@/lib/cookies";

export type Collapsible = "offcanvas" | "icon" | "none";
export type Variant = "inset" | "sidebar" | "floating";

// Cookie constants following the pattern from sidebar.tsx
const LAYOUT_COLLAPSIBLE_COOKIE_NAME = "layout_collapsible";
const LAYOUT_VARIANT_COOKIE_NAME = "layout_variant";
const LAYOUT_COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

// Default values
const DEFAULT_VARIANT = "inset";
const DEFAULT_COLLAPSIBLE = "icon";

type LayoutContextType = {
  resetLayout: () => void;

  defaultCollapsible: Collapsible;
  collapsible: Collapsible;
  setCollapsible: (collapsible: Collapsible) => void;

  defaultVariant: Variant;
  variant: Variant;
  setVariant: (variant: Variant) => void;
};

const LayoutContext = createContext<LayoutContextType | null>(null);

type LayoutProviderProps = {
  children: React.ReactNode;
};

export function LayoutProvider({ children }: LayoutProviderProps) {
  // 2. Initialize state with server-safe default values.
  const [collapsible, _setCollapsible] = useState<Collapsible>(DEFAULT_COLLAPSIBLE);
  const [variant, _setVariant] = useState<Variant>(DEFAULT_VARIANT);

  // 3. Use useEffect to safely update state from cookies on the client side.
  useEffect(() => {
    const savedCollapsible = getCookie(LAYOUT_COLLAPSIBLE_COOKIE_NAME);
    if (savedCollapsible) {
      _setCollapsible(savedCollapsible as Collapsible);
    }

    const savedVariant = getCookie(LAYOUT_VARIANT_COOKIE_NAME);
    if (savedVariant) {
      _setVariant(savedVariant as Variant);
    }
  }, []); // The empty array [] ensures this runs only once after the component mounts on the client.

  const setCollapsible = (newCollapsible: Collapsible) => {
    _setCollapsible(newCollapsible);
    setCookie(
      LAYOUT_COLLAPSIBLE_COOKIE_NAME,
      newCollapsible,
      LAYOUT_COOKIE_MAX_AGE,
    );
  };

  const setVariant = (newVariant: Variant) => {
    _setVariant(newVariant);
    setCookie(LAYOUT_VARIANT_COOKIE_NAME, newVariant, LAYOUT_COOKIE_MAX_AGE);
  };

  const resetLayout = () => {
    setCollapsible(DEFAULT_COLLAPSIBLE);
    setVariant(DEFAULT_VARIANT);
  };

  const contextValue: LayoutContextType = {
    resetLayout,
    defaultCollapsible: DEFAULT_COLLAPSIBLE,
    collapsible,
    setCollapsible,
    defaultVariant: DEFAULT_VARIANT,
    variant,
    setVariant,
  };

  return <LayoutContext.Provider value={contextValue}>{children}</LayoutContext.Provider>;
}

// Define the hook for the provider
// eslint-disable-next-line react-refresh/only-export-components
export function useLayout() {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error("useLayout must be used within a LayoutProvider");
  }
  return context;
}
