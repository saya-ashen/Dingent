import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getLogStatistics, getLogs, clearAllLogs } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/layout/Page";
import { toast } from "sonner";

const levelColors: Record<string, string> = {
    DEBUG: "#808080",
    INFO: "#0066CC",
    WARNING: "#FF8C00",
    ERROR: "#FF4444",
    CRITICAL: "#CC0000"
};

const LEVELS = ["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

export default function LogsPage() {
    const qc = useQueryClient();
    const [autoRefresh, setAutoRefresh] = useState(false);

    const statsQ = useQuery({
        queryKey: ["log-stats"],
        queryFn: getLogStatistics,
        refetchInterval: autoRefresh ? 10_000 : false
    });

    const [level, setLevel] = useState<string>("All");
    const [module, setModule] = useState<string>("");
    const [search, setSearch] = useState<string>("");
    const [limit, setLimit] = useState<number>(100);

    const logsQ = useQuery({
        queryKey: ["logs", level, module, search, limit],
        queryFn: () =>
            getLogs({
                level: level === "All" ? null : level,
                module: module.trim() || null,
                search: search.trim() || null,
                limit
            }),
        staleTime: 2_000,
        refetchInterval: autoRefresh ? 10_000 : false
    });

    const total = statsQ.data?.total_logs ?? 0;
    const byLevelEntries = useMemo(() => Object.entries(statsQ.data?.by_level ?? {}), [statsQ.data]);

    return (
        <div className="space-y-4">
            <PageHeader
                title="System Logs"
                description="Inspect logs and filter by level, module, or keywords."
                actions={
                    <div className="flex items-center gap-2">
                        <Button
                            variant={autoRefresh ? "default" : "outline"}
                            onClick={() => setAutoRefresh(v => !v)}
                        >
                            {autoRefresh ? "Auto Refresh: ON" : "Auto Refresh: OFF"}
                        </Button>
                        <Button
                            onClick={async () => {
                                await qc.invalidateQueries({ queryKey: ["logs"] });
                                await qc.invalidateQueries({ queryKey: ["log-stats"] });
                            }}
                        >
                            Refresh
                        </Button>
                        <Button
                            variant="secondary"
                            onClick={async () => {
                                const ok = await clearAllLogs();
                                if (ok) {
                                    toast.success("All logs cleared");
                                    await qc.invalidateQueries({ queryKey: ["logs"] });
                                    await qc.invalidateQueries({ queryKey: ["log-stats"] });
                                } else {
                                    toast.info("Clear All Logs not implemented on backend");
                                }
                            }}
                        >
                            Clear All
                        </Button>
                    </div>
                }
            />

            <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr]">
                <div className="rounded border p-3">
                    <div className="font-medium mb-2">Log Statistics</div>
                    {total > 0 ? (
                        <>
                            <div className="text-3xl font-bold">{total}</div>
                            {!!byLevelEntries.length && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {byLevelEntries.map(([lvl, count]) => (
                                        <span
                                            key={lvl}
                                            className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm"
                                            style={{ borderColor: levelColors[lvl] || "#999", color: levelColors[lvl] || "#999" }}
                                        >
                                            {lvl} <span className="font-semibold">{count}</span>
                                        </span>
                                    ))}
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="text-sm text-muted-foreground">No logs available</div>
                    )}
                </div>

                <div className="rounded border p-3">
                    <div className="font-medium mb-2">Filter</div>
                    <div className="grid grid-cols-1 gap-2">
                        <div className="flex flex-wrap gap-2">
                            {LEVELS.map(l => (
                                <button
                                    key={l}
                                    className={`rounded-full border px-3 py-1 text-sm ${l === level ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                                    onClick={() => setLevel(l)}
                                >
                                    {l}
                                </button>
                            ))}
                        </div>
                        <Input placeholder="Module (e.g., config_manager)" value={module} onChange={(e) => setModule(e.target.value)} />
                        <Input placeholder="Search in message..." value={search} onChange={(e) => setSearch(e.target.value)} />
                        <Input type="number" min={10} max={500} step={10} value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
                    </div>
                </div>
            </div>

            <div className="space-y-2">
                {logsQ.isLoading && <div>Loading logs...</div>}
                {logsQ.error && <div className="text-red-600">Failed to load logs</div>}
                {logsQ.data && logsQ.data.length > 0 && (
                    <div className="text-sm font-medium">Showing {logsQ.data.length} logs</div>
                )}
                {logsQ.data?.map((log, idx) => {
                    const color = levelColors[log.level] || "#000000";
                    return (
                        <details key={idx} className="rounded border p-2">
                            <summary className="cursor-pointer">
                                <span className="font-semibold" style={{ color }}>{log.level}</span>{" "}
                                <span className="text-muted-foreground">[{(log.timestamp || "").slice(0, 19)}]</span>{" "}
                                <code>{log.module || "unknown"}.{log.function || "unknown"}</code>{" "}
                                - {log.message?.slice(0, 100)}
                            </summary>
                            <div className="mt-2 space-y-1">
                                <div><span className="font-semibold">Level:</span> <span style={{ color }}>{log.level}</span></div>
                                <div><span className="font-semibold">Timestamp:</span> {log.timestamp}</div>
                                <div><span className="font-semibold">Module:</span> <code>{log.module}</code></div>
                                <div><span className="font-semibold">Function:</span> <code>{log.function}</code></div>
                                <div className="flex items-center justify-between">
                                    <div className="font-semibold">Message:</div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => {
                                            navigator.clipboard.writeText(log.message || "");
                                            toast.success("Message copied");
                                        }}
                                    >
                                        Copy
                                    </Button>
                                </div>
                                <pre className="rounded bg-muted p-2 text-sm whitespace-pre-wrap">{log.message}</pre>
                                {log.context && Object.keys(log.context).length > 0 && (
                                    <>
                                        <div className="font-semibold">Context:</div>
                                        <pre className="rounded bg-muted p-2 text-sm whitespace-pre-wrap">{JSON.stringify(log.context, null, 2)}</pre>
                                    </>
                                )}
                                {log.correlation_id && (
                                    <div><span className="font-semibold">Correlation ID:</span> <code>{log.correlation_id}</code></div>
                                )}
                            </div>
                        </details>
                    );
                })}
                {logsQ.data && logsQ.data.length === 0 && (
                    <div className="text-sm text-muted-foreground">No logs match the current filters.</div>
                )}
            </div>
        </div>
    );
}
