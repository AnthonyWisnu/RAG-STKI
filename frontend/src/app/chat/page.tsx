"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowUp,
  Database,
  FileSearch,
  Layers,
  MessageSquare,
  Sparkles
} from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { sendChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatResponse, Citation, RetrievalStrategy } from "@/types";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
};

const quickQuestions = [
  "Siapa top scorer La Liga musim ini?",
  "Siapa pemain statistik mirip Ferran Torres tetapi market value lebih rendah?",
  "Bandingkan Erling Haaland dan Kylian Mbappé sebagai Forward",
  "Berapa estimasi nilai pasar Yamal?"
];

const strategyMeta: Record<
  string,
  {
    label: string;
    icon: typeof Database;
    className: string;
  }
> = {
  kg_only: {
    label: "Knowledge Graph",
    icon: Database,
    className: "border-chart-2 text-chart-2"
  },
  vector_only: {
    label: "Semantic Search",
    icon: FileSearch,
    className: "border-chart-4 text-chart-4"
  },
  hybrid: {
    label: "Hybrid",
    icon: Layers,
    className: "border-accent text-accent"
  },
  valuation_reasoning: {
    label: "LLM Valuasi",
    icon: Sparkles,
    className: "border-chart-5 text-chart-5"
  }
};

function strategyBadge(strategy: RetrievalStrategy) {
  const meta = strategyMeta[strategy] ?? strategyMeta.hybrid;
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-panel border bg-background-secondary px-2 py-1 text-[11px]",
        meta.className
      )}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="text-xs font-medium text-text-secondary transition-colors hover:text-accent"
      >
        {open ? "Sembunyikan sumber" : `Lihat sumber (${citations.length})`}
      </button>
      {open ? (
        <div className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <div
              key={`${citation.source ?? "source"}-${index}`}
              className="rounded-panel border border-border bg-background-primary p-3 text-xs text-text-secondary"
            >
              <div className="font-mono text-text-primary">
                {citation.label ?? citation.source ?? `Sumber ${index + 1}`}
              </div>
              <pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-text-secondary">
                {JSON.stringify(citation, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex w-fit gap-1 rounded-panel border border-border px-4 py-3">
      <span className="typing-dot h-2 w-2 rounded-full bg-text-secondary" />
      <span className="typing-dot h-2 w-2 rounded-full bg-text-secondary" />
      <span className="typing-dot h-2 w-2 rounded-full bg-text-secondary" />
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const assistant = message.role === "assistant";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("flex", assistant ? "justify-start" : "justify-end")}
    >
      <div className={cn("max-w-[86%]", assistant ? "text-left" : "text-right")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            assistant
              ? "rounded-bl rounded-bl-panel border border-border bg-transparent text-text-primary"
              : "rounded-br rounded-br-panel bg-background-tertiary text-text-primary"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.response ? (
          <div className="mt-2">
            {strategyBadge(message.response.strategy_used)}
            <CitationList citations={message.response.citations} />
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Tanyakan statistik, profil pemain, perbandingan, top performers, atau reasoning valuasi untuk lima liga top Eropa."
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant" && message.response),
    [messages]
  );

  async function submitQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    setError(null);
    setInput("");
    setLoading(true);
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed
    };
    setMessages((current) => [...current, userMessage]);

    try {
      const response = await sendChatMessage({ question: trimmed });
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        response
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Terjadi kesalahan saat mengambil data.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(input);
  }

  function handleInput(value: string) {
    setInput(value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 132)}px`;
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-96px)] gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="flex min-h-[calc(100vh-96px)] flex-col overflow-hidden rounded-panel border border-border bg-background-secondary">
        <div className="border-b border-border px-4 py-3">
          <SectionHeading title="Percakapan" />
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {loading ? <TypingIndicator /> : null}
        </div>

        {error ? (
          <div className="mx-4 mb-3 flex items-center gap-2 rounded-panel border border-status-old bg-background-primary px-3 py-2 text-sm text-text-primary">
            <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
            <span className="min-w-0 flex-1">{error}</span>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="border-t border-border bg-background-primary p-4">
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => handleInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void submitQuestion(input);
                }
              }}
              rows={1}
              placeholder="Tanya tentang pemain, statistik, atau valuasi..."
              className="max-h-32 min-h-14 w-full resize-none rounded-panel border border-border bg-background-secondary py-4 pl-4 pr-14 text-sm text-text-primary placeholder:text-text-muted transition-colors focus:border-accent focus:outline-none"
            />
            <Button
              type="submit"
              variant="icon"
              disabled={loading || input.trim().length === 0}
              className="absolute bottom-2 right-2"
              aria-label="Kirim pertanyaan"
            >
              <ArrowUp className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </form>
      </section>

      <aside className="space-y-5">
        <section className="rounded-panel border border-border bg-background-secondary p-4">
          <SectionHeading title="Contoh Pertanyaan" />
          <div className="mt-4 space-y-2">
            {quickQuestions.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => void submitQuestion(question)}
                className="flex w-full items-center gap-3 rounded-panel border border-border bg-background-primary px-3 py-3 text-left text-sm text-text-secondary transition-colors hover:bg-background-tertiary hover:text-text-primary"
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
                <span>{question}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-panel border border-border bg-background-secondary p-4">
          <SectionHeading title="Konteks Terakhir" />
          {latestAssistant?.response ? (
            <div className="mt-4 space-y-3 text-sm text-text-secondary">
              <div className="flex items-center justify-between rounded-panel border border-border bg-background-primary px-3 py-2">
                <span>Strategi</span>
                {strategyBadge(latestAssistant.response.strategy_used)}
              </div>
              <div className="rounded-panel border border-border bg-background-primary p-3">
                <div className="font-mono text-xs text-text-primary">
                  Data tersedia: {latestAssistant.response.data_available ? "Ya" : "Tidak"}
                </div>
                <div className="mt-2 font-mono text-xs">
                  Bahasa: {latestAssistant.response.language.toUpperCase()}
                </div>
                {latestAssistant.response.fallback_signal ? (
                  <div className="mt-2 text-xs text-status-stale">
                    {latestAssistant.response.fallback_signal}
                  </div>
                ) : null}
              </div>
              <div className="rounded-panel border border-border bg-background-primary p-3">
                <div className="text-xs uppercase tracking-widest text-text-muted">
                  Citation
                </div>
                <div className="mt-1 font-mono text-lg text-text-primary">
                  {latestAssistant.response.citations.length}
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm leading-relaxed text-text-secondary">
              Konteks retrieval akan tampil setelah pertanyaan pertama dijawab.
            </p>
          )}
        </section>
      </aside>
    </div>
  );
}
