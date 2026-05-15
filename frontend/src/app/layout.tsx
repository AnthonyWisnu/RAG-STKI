import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "ScoutRAG",
  description: "Football Knowledge Graph dan RAG untuk statistik serta valuasi pemain."
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="id">
      <body>
        <Sidebar />
        <div className="min-h-screen pb-20 md:pb-0 lg:pl-64">
          <Header />
          <main className="mx-auto min-h-[calc(100vh-56px)] w-full max-w-7xl px-4 py-5 lg:px-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
