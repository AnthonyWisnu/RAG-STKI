"use client";

import { LockKeyhole, LogIn } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { error?: string } | null;
        setError(payload?.error ?? "Login gagal.");
        return;
      }

      const next = new URLSearchParams(window.location.search).get("next") || "/chat";
      router.replace(next.startsWith("/") ? next : "/chat");
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background-primary px-4 py-10">
      <div className="w-full max-w-md rounded-panel border border-border bg-background-secondary p-6 shadow-2xl shadow-black/30">
        <div className="mb-7">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-panel border border-accent bg-accent-dim text-accent">
            <LockKeyhole className="h-5 w-5" aria-hidden="true" />
          </div>
          <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
            ScoutRAG Access
          </p>
          <h1 className="mt-2 font-display text-4xl font-bold leading-none text-text-primary">
            Login
          </h1>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-widest text-text-secondary">
              Username
            </span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              className="h-12 w-full rounded-panel border border-border bg-background-primary px-4 text-text-primary placeholder:text-text-muted"
              placeholder="admin"
              required
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-widest text-text-secondary">
              Password
            </span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
              className="h-12 w-full rounded-panel border border-border bg-background-primary px-4 text-text-primary placeholder:text-text-muted"
              placeholder="Masukkan password"
              required
            />
          </label>

          {error ? (
            <div className="rounded-panel border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          <Button type="submit" variant="primary" className="w-full" disabled={loading}>
            <LogIn className="h-4 w-4" aria-hidden="true" />
            {loading ? "Memproses..." : "Masuk"}
          </Button>
        </form>
      </div>
    </div>
  );
}

