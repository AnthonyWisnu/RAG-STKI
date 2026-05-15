import { UserRound } from "lucide-react";
import type { ReactNode } from "react";

import type { PlayerSummary } from "@/types";
import {
  cn,
  formatEuro,
  formatNumber,
  getPositionAccentClass
} from "@/lib/utils";
import { PositionBadge } from "@/components/player/PositionBadge";
import { StatBadge } from "@/components/player/StatBadge";

type PlayerCardProps = {
  player: PlayerSummary;
  action?: ReactNode;
  compact?: boolean;
  className?: string;
};

export function PlayerCard({ player, action, compact = false, className }: PlayerCardProps) {
  return (
    <article
      className={cn(
        "flex items-center gap-4 rounded-panel border border-border bg-background-secondary p-4 transition-colors hover:bg-background-tertiary",
        "border-l-4",
        getPositionAccentClass(player.position),
        className
      )}
    >
      <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-background-primary text-text-secondary">
        {player.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={player.photo_url}
            alt={player.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <UserRound className="h-5 w-5" aria-hidden="true" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate font-display text-lg font-bold leading-none text-text-primary">
            {player.name}
          </h3>
          <PositionBadge position={player.position} />
        </div>
        <p className="mt-1 truncate text-sm text-text-secondary">
          {[player.club, player.league].filter(Boolean).join(" - ") || "Klub tidak tersedia"}
        </p>
        {!compact ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <StatBadge label="Menit" value={formatNumber(player.minutes)} />
            <StatBadge label="Gol" value={formatNumber(player.goals)} />
            <StatBadge label="Assist" value={formatNumber(player.assists)} />
            <StatBadge label="Nilai" value={formatEuro(player.market_value_eur)} />
          </div>
        ) : null}
      </div>

      {action ? <div className="shrink-0">{action}</div> : null}
    </article>
  );
}
