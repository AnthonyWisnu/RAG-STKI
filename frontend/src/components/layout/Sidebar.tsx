"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Search,
  Shield,
  Sparkles,
  TrendingUp,
  Trophy,
  Users
} from "lucide-react";

import { cn } from "@/lib/utils";
import { DataFreshnessBadge } from "@/components/layout/DataFreshnessBadge";

const navItems = [
  { href: "/chat", label: "Tanya Jawab", icon: MessageSquare },
  { href: "/compare", label: "Bandingkan", icon: Users },
  { href: "/search", label: "Cari Pemain", icon: Search },
  { href: "/valuation", label: "Analisis Valuasi", icon: TrendingUp },
  { href: "/predict", label: "Estimasi Nilai", icon: Sparkles },
  { href: "/top", label: "Top Performers", icon: Trophy },
  { href: "/club", label: "Profil Klub", icon: Shield }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-background-secondary lg:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Link href="/chat" className="font-display text-2xl font-bold uppercase text-text-primary">
            ScoutRAG
          </Link>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-panel border-l-2 px-3 py-3 text-sm transition-colors",
                  active
                    ? "border-accent bg-accent-dim text-accent"
                    : "border-transparent text-text-secondary hover:bg-background-tertiary hover:text-text-primary"
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-3">
          <DataFreshnessBadge />
        </div>
      </aside>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-border bg-background-secondary px-2 py-2 md:hidden">
        {navItems.slice(0, 5).map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 rounded-panel px-2 py-2 text-[11px]",
                active ? "bg-accent-dim text-accent" : "text-text-secondary"
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
