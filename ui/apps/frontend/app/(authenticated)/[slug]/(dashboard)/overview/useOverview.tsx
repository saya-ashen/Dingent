"use client";

import { useEffect, useState } from "react";

import { useParams } from "next/navigation";
import { getClientApi } from "@/lib/api/client";

import type { OverviewData } from "@repo/api-client";

export function useOverview() {
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi();
  const wsApi = api.forWorkspace(slug);
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = () => {
    setLoading(true);

    setError(null);

    wsApi.overview.get()
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
