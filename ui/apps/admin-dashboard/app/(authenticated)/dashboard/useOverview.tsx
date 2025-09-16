"use client";

import { useEffect, useState } from "react";

import { getOverview } from "@repo/api-client";

import type { OverviewData } from "@repo/api-client";

export function useOverview() {
  const [data, setData] = useState<OverviewData | null>(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const reload = () => {
    setLoading(true);

    setError(null);

    getOverview()
      .then((d) => {
        setData(d);
      })

      .catch((e: Error) => {
        setError(e.message);
      })

      .finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
  }, []);

  return { data, loading, error, reload };
}
