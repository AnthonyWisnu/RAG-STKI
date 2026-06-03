"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <div className="min-h-screen pb-20 md:pb-0 lg:pl-64">
        <Header />
        <main className="mx-auto min-h-[calc(100vh-56px)] w-full max-w-7xl px-4 py-5 lg:px-8">
          {children}
        </main>
      </div>
    </>
  );
}

