"use client";

import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/chat": "Tanya Jawab",
  "/compare": "Bandingkan Pemain",
  "/search": "Cari Pemain",
  "/valuation": "Analisis Valuasi",
  "/predict": "Estimasi Nilai",
  "/top": "Top Performers",
  "/club": "Profil Klub"
};

export function Header() {
  const pathname = usePathname();
  const title = titles[pathname] ?? "Football KG-RAG";

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-background-primary px-4 lg:px-8">
      <div>
        <p className="text-[11px] uppercase tracking-widest text-text-muted">
          Knowledge Graph dan RAG
        </p>
        <h1 className="font-display text-2xl font-bold leading-none text-text-primary">
          {title}
        </h1>
      </div>
      <div className="hidden items-center gap-2 font-mono text-xs text-text-secondary sm:flex">
        <span>Big 5 Europe</span>
        <span className="h-1 w-1 rounded-full bg-accent" />
        <span>2023-2026</span>
      </div>
    </header>
  );
}
