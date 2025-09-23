"use client";

import { useAuthStore } from "@repo/store";
import { useEffect } from "react";

// This component ensures that the store is hydrated from cookies on the client side.
function StoreInitializer() {
  // useEffect with an empty dependency array runs only once on the client
  useEffect(() => {
    useAuthStore.getState().hydrate();
  }, []);

  return null; // This component renders nothing
}

export default StoreInitializer;
