import { Suspense } from "react";
import { MarketPageContent } from "./market-client-page";
import { LoadingSkeleton } from "@repo/ui/components"; // Or your preferred loading component

export default function MarketPage() {
  return (
    <Suspense fallback={<LoadingSkeleton lines={10} />}>
      <MarketPageContent />
    </Suspense>
  );
}
