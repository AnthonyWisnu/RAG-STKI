import { Shield } from "lucide-react";

import { formatEuro, formatNumber } from "@/lib/utils";
import type { ClubDetailResponse } from "@/types";

type ClubHeaderProps = {
  detail: ClubDetailResponse;
};

export function ClubHeader({ detail }: ClubHeaderProps) {
  return (
    <section className="flex flex-col gap-4 rounded-panel border border-border bg-background-secondary p-5 md:flex-row md:items-center">
      <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-panel border border-border bg-background-primary text-accent">
        <Shield className="h-8 w-8" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <h2 className="truncate font-display text-4xl font-bold leading-none text-text-primary">
          {detail.club.name}
        </h2>
        <p className="mt-2 text-sm text-text-secondary">
          {detail.club.country ?? "Negara tidak tersedia"} - Didirikan: {detail.club.founded_year ?? "Tidak tersedia"}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:w-80">
        <div className="rounded-panel border border-border bg-background-primary p-3">
          <div className="text-xs uppercase tracking-widest text-text-muted">Pemain</div>
          <div className="mt-2 font-mono text-xl text-text-primary">{formatNumber(detail.squad.length)}</div>
        </div>
        <div className="rounded-panel border border-border bg-background-primary p-3">
          <div className="text-xs uppercase tracking-widest text-text-muted">Nilai Squad</div>
          <div className="mt-2 font-mono text-xl text-accent">{formatEuro(detail.total_squad_value)}</div>
        </div>
      </div>
    </section>
  );
}
