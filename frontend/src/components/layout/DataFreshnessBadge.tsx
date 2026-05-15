"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle, Info, RefreshCw } from "lucide-react";

import { getHealth, getRefreshStatus, startRefresh } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { HealthResponse, RefreshStatus } from "@/types";

function getAgeInDays(lastRefresh: string | null): number | null {
  if (!lastRefresh) {
    return null;
  }

  const timestamp = new Date(lastRefresh).getTime();
  if (Number.isNaN(timestamp)) {
    return null;
  }

  return Math.max(0, Math.floor((Date.now() - timestamp) / 86_400_000));
}

export function DataFreshnessBadge() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [refreshStatus, setRefreshStatus] = useState<RefreshStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((response) => {
        if (mounted) {
          setHealth(response);
        }
      })
      .catch(() => {
        if (mounted) {
          setHealth(null);
        }
      });
    getRefreshStatus()
      .then((response) => {
        if (mounted) {
          setRefreshStatus(response);
        }
      })
      .catch(() => {
        if (mounted) {
          setRefreshStatus(null);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const response = await startRefresh();
      setRefreshStatus(response.status);
      const nextStatus = await getRefreshStatus();
      setRefreshStatus(nextStatus);
      const nextHealth = await getHealth();
      setHealth(nextHealth);
    } finally {
      setRefreshing(false);
    }
  }

  const ageInDays = useMemo(() => getAgeInDays(health?.last_refresh ?? null), [health]);
  const status = ageInDays === null ? "old" : ageInDays <= 7 ? "fresh" : ageInDays <= 14 ? "stale" : "old";
  const dotClass = {
    fresh: "bg-status-fresh",
    stale: "bg-status-stale",
    old: "bg-status-old"
  }[status];
  const Icon = status === "fresh" ? CheckCircle : AlertTriangle;
  const label = ageInDays === null ? "Data belum terbaca" : `Data ${ageInDays} hari lalu`;

  return (
    <div className="relative space-y-2">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 rounded-panel border border-border bg-background-primary px-3 py-2 text-left text-xs text-text-secondary transition-colors hover:bg-background-tertiary"
        aria-label="Lihat informasi freshness data"
      >
        <span className={cn("h-2 w-2 rounded-full", dotClass)} />
        <span className="min-w-0 flex-1 truncate">{label}</span>
        <Info className="h-4 w-4" aria-hidden="true" />
      </button>

      <button
        type="button"
        onClick={() => void handleRefresh()}
        disabled={refreshing || refreshStatus?.status === "running"}
        className="flex w-full items-center justify-center gap-2 rounded-panel border border-accent bg-accent-dim px-3 py-2 text-xs font-medium text-accent transition-colors hover:bg-background-tertiary disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw
          className={cn("h-4 w-4", refreshing || refreshStatus?.status === "running" ? "animate-spin" : "")}
          aria-hidden="true"
        />
        {refreshing || refreshStatus?.status === "running" ? "Memperbarui..." : "Perbarui Data"}
      </button>

      {open ? (
        <div className="absolute bottom-full left-0 z-40 mb-3 w-72 rounded-panel border border-border bg-background-secondary p-4 shadow-panel">
          <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
            <Icon className="h-4 w-4 text-accent" aria-hidden="true" />
            Status data
          </div>
          <p className="mt-2 text-sm text-text-secondary">
            {health?.data_freshness_badge ?? "Backend belum mengirim status data."}
          </p>
          <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-xs text-text-secondary">
            <span>Stats {health?.stats_records ?? "-"}</span>
            <span>Value {health?.valuation_records ?? "-"}</span>
            <span>Pemain {health?.mapped_players ?? "-"}</span>
          </div>
          {refreshStatus?.skipped_reason ? (
            <p className="mt-3 text-xs leading-relaxed text-status-stale">
              {refreshStatus.skipped_reason}
            </p>
          ) : null}
          {refreshStatus?.error ? (
            <p className="mt-3 text-xs leading-relaxed text-status-old">
              {refreshStatus.error}
            </p>
          ) : null}
          <p className="mt-3 text-[11px] leading-relaxed text-text-muted">
            Refresh memakai state terakhir dan tidak menjalankan initial setup ulang.
          </p>
        </div>
      ) : null}
    </div>
  );
}
