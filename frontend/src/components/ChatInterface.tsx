"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, FileWarning, GraduationCap, Loader2, Send, Trash2 } from "lucide-react";
import type { DocumentsResponse, Message } from "@/types";
import ChatMessage from "./ChatMessage";
import SuggestedQuestions from "./SuggestedQuestions";

const MAX_LEN = 1000;

export const QUICK_LINKS = [
  { label: "Eligibility", question: "What are the eligibility criteria for campus placements?" },
  { label: "Placement rules", question: "Can students attend multiple company drives?" },
  { label: "Offer policies", question: "What happens after accepting a placement offer?" },
];

interface Props {
  messages: Message[];
  loading: boolean;
  onSend: (question: string) => void;
  onClear: () => void;
  docs: DocumentsResponse | null;
  docsLoading: boolean;
  docsError: string | null;
  recent: string[];
}

function PolicyStatus({
  docs,
  loading,
  error,
}: {
  docs: DocumentsResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-line bg-surface p-4 shadow-card" aria-busy="true">
        <div className="skeleton h-4 w-32" />
        <div className="skeleton mt-3 h-6 w-48" />
        <div className="skeleton mt-2 h-4 w-40" />
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" className="flex gap-3 rounded-2xl border border-danger/30 bg-danger-soft p-4 text-sm">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-hidden />
        <div>
          <p className="font-semibold text-danger">Policy status unavailable</p>
          <p className="text-ink-soft">{error}</p>
        </div>
      </div>
    );
  }
  const ready = (docs?.documents ?? []).filter((d) => d.status === "ready" && d.is_current);
  if (!docs || docs.indexed_documents === 0 || ready.length === 0) {
    return (
      <div className="flex gap-3 rounded-2xl border border-warn/30 bg-warn-soft p-4 text-sm">
        <FileWarning className="mt-0.5 h-5 w-5 shrink-0 text-warn" aria-hidden />
        <div>
          <p className="font-semibold text-warn">No placement policy indexed yet</p>
          <p className="text-ink-soft">
            Questions can’t be answered until an administrator uploads the official policy PDF.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-card">
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ok">
        <CheckCircle2 className="h-4 w-4" aria-hidden /> Policy ready
      </p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">
        {docs.indexed_documents}{" "}
        <span className="text-sm font-normal text-muted">
          indexed document{docs.indexed_documents === 1 ? "" : "s"}
        </span>
      </p>
      <ul className="mt-2 space-y-1 text-sm text-ink-soft">
        {ready.map((d) => (
          <li key={`${d.document_id}-${d.version}`} className="truncate" title={d.filename}>
            {d.filename} · v{d.version} · updated {new Date(d.updated_at).toLocaleDateString()}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ChatInterface({
  messages,
  loading,
  onSend,
  onClear,
  docs,
  docsLoading,
  docsError,
  recent,
}: Props) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const empty = messages.length === 0;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading]);

  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const q = text.trim();
    if (!q || loading) return;
    onSend(q);
    setText("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const asked = messages.filter((m) => m.role === "user").map((m) => m.content);
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto w-full max-w-3xl">
          {empty ? (
            <div className="rise space-y-8">
              <header>
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-white shadow-card">
                  <GraduationCap className="h-6 w-6" aria-hidden />
                </div>
                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                  Welcome to BMSCE Campus
                </h1>
                <p className="mt-2 max-w-xl text-base text-muted">
                  Ask about your placement policy in plain language. Every answer is drawn from the
                  official document.
                </p>
              </header>

              <PolicyStatus docs={docs} loading={docsLoading} error={docsError} />

              <section aria-label="Quick links">
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                  Quick links
                </h2>
                <div className="grid gap-2.5 sm:grid-cols-3">
                  {QUICK_LINKS.map((l) => (
                    <button
                      key={l.label}
                      type="button"
                      onClick={() => onSend(l.question)}
                      disabled={loading}
                      className="rounded-xl border border-line bg-surface px-4 py-3 text-left shadow-card transition hover:border-accent hover:bg-accent-soft disabled:opacity-50"
                    >
                      <span className="block text-sm font-semibold">{l.label}</span>
                      <span className="mt-0.5 block text-xs text-muted">{l.question}</span>
                    </button>
                  ))}
                </div>
              </section>

              <SuggestedQuestions onSelect={onSend} disabled={loading} />

              {recent.length > 0 && (
                <section aria-label="Recently asked questions">
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                    Recently asked on this device
                  </h2>
                  <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
                    {recent.map((q) => (
                      <li key={q}>
                        <button
                          type="button"
                          onClick={() => onSend(q)}
                          disabled={loading}
                          className="w-full truncate px-4 py-2.5 text-left text-sm text-ink-soft hover:bg-canvas"
                        >
                          {q}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          ) : (
            <div role="log" aria-live="polite" aria-label="Conversation" className="space-y-6">
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}

              {loading && (
                <div className="flex gap-3" role="status" aria-label="BMSCE Campus is searching the policy">
                  <div className="mt-1 hidden h-8 w-8 shrink-0 sm:block" aria-hidden />
                  <div className="w-full max-w-md space-y-2 rounded-2xl border border-line bg-surface p-4 shadow-card">
                    <p className="flex items-center gap-2 text-sm text-muted">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Searching the policy…
                    </p>
                    <div className="skeleton h-3 w-full" />
                    <div className="skeleton h-3 w-4/5" />
                  </div>
                </div>
              )}

              {!loading && lastAssistant && !lastAssistant.isError && (
                <SuggestedQuestions
                  onSelect={onSend}
                  exclude={asked}
                  title="Suggested follow-ups"
                  limit={3}
                />
              )}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-line bg-surface/90 px-4 py-3 backdrop-blur sm:px-8">
        <form onSubmit={submit} className="mx-auto w-full max-w-3xl">
          <label htmlFor="question" className="sr-only">
            Ask a question about the placement policy
          </label>
          <div className="flex items-end gap-2 rounded-2xl border border-line bg-surface p-2 shadow-card focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
            <textarea
              id="question"
              ref={areaRef}
              rows={1}
              value={text}
              maxLength={MAX_LEN}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKey}
              placeholder="Ask about eligibility, CGPA, offers, internships…"
              className="max-h-44 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-[0.95rem] outline-none placeholder:text-muted/80"
            />
            {!empty && (
              <button
                type="button"
                onClick={onClear}
                disabled={loading}
                aria-label="Clear conversation"
                title="Clear conversation"
                className="rounded-xl p-2.5 text-muted transition hover:bg-canvas hover:text-danger disabled:opacity-40"
              >
                <Trash2 className="h-5 w-5" aria-hidden />
              </button>
            )}
            <button
              type="submit"
              disabled={!text.trim() || loading}
              className="inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Send className="h-4 w-4" aria-hidden />
              )}
              <span>{loading ? "Asking" : "Ask"}</span>
            </button>
          </div>
          <p className="mt-1.5 flex justify-between px-1 text-xs text-muted">
            <span>Enter to send · Shift+Enter for a new line</span>
            <span className="tabular-nums">
              {text.length}/{MAX_LEN}
            </span>
          </p>
        </form>
      </div>
    </div>
  );
}
