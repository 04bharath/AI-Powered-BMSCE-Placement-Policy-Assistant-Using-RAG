"use client";

import { FileText, GraduationCap, History, MessageSquare, X, Lock } from "lucide-react";
import type { DocumentsResponse } from "@/types";
import { QUICK_LINKS } from "./ChatInterface";

export type View = "chat" | "documents";

interface Props {
  view: View;
  onViewChange: (v: View) => void;
  recent: string[];
  onAsk: (q: string) => void;
  docs: DocumentsResponse | null;
  docsLoading: boolean;
  docsError: string | null;
  open: boolean;
  onClose: () => void;
  isAdmin: boolean;
}

export default function Sidebar({
  view,
  onViewChange,
  recent,
  onAsk,
  docs,
  docsLoading,
  docsError,
  open,
  onClose,
  isAdmin,
}: Props) {
  const nav = (v: View, label: string, Icon: typeof MessageSquare) => (
    <button
      type="button"
      onClick={() => {
        onViewChange(v);
        onClose();
      }}
      aria-current={view === v ? "page" : undefined}
      className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
        view === v ? "bg-accent-soft text-accent-strong" : "text-ink-soft hover:bg-canvas"
      }`}
    >
      <Icon className="h-[18px] w-[18px]" aria-hidden /> {label}
    </button>
  );

  let status: { dot: string; text: string };
  if (docsLoading) status = { dot: "bg-muted/40", text: "Checking policy…" };
  else if (docsError) status = { dot: "bg-danger", text: "Server unreachable" };
  else if (!docs || docs.indexed_documents === 0) status = { dot: "bg-warn", text: "No policy indexed" };
  else
    status = {
      dot: "bg-ok",
      text: `${docs.indexed_documents} document${docs.indexed_documents === 1 ? "" : "s"} indexed`,
    };

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-ink/40 lg:hidden" onClick={onClose} aria-hidden />
      )}
      <aside
        aria-label="Sidebar"
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-line bg-surface transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <div className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent text-white">
              <GraduationCap className="h-5 w-5" aria-hidden />
            </span>
            <div className="leading-tight">
              <p className="text-base font-semibold tracking-tight">BMSCE Campus</p>
              <p className="text-xs text-muted">Placement policy assistant</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="rounded-lg p-1.5 text-muted hover:bg-canvas lg:hidden"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <nav aria-label="Main" className="space-y-1 px-3">
          {nav("chat", "Ask the policy", MessageSquare)}
          {nav("documents", "Documents", FileText)}
        </nav>

        <div className="mt-6 min-h-0 flex-1 space-y-6 overflow-y-auto px-5">
          <section aria-label="Quick links">
            <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted">Quick links</h2>
            <ul className="space-y-0.5">
              {QUICK_LINKS.map((l) => (
                <li key={l.label}>
                  <button
                    type="button"
                    onClick={() => {
                      onAsk(l.question);
                      onClose();
                    }}
                    className="w-full rounded-lg px-2 py-1.5 text-left text-sm text-ink-soft hover:bg-canvas hover:text-accent-strong"
                  >
                    {l.label}
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section aria-label="Recent questions">
            <h2 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted">
              <History className="h-3.5 w-3.5" aria-hidden /> Recent
            </h2>
            {recent.length === 0 ? (
              <p className="text-sm text-muted">Questions you ask will appear here.</p>
            ) : (
              <ul className="space-y-0.5">
                {recent.map((q) => (
                  <li key={q}>
                    <button
                      type="button"
                      title={q}
                      onClick={() => {
                        onAsk(q);
                        onClose();
                      }}
                      className="w-full truncate rounded-lg px-2 py-1.5 text-left text-sm text-ink-soft hover:bg-canvas"
                    >
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="border-t border-line px-5 py-4 text-sm">
          <p className="flex items-center gap-2" role="status">
            <span className={`h-2.5 w-2.5 rounded-full ${status.dot}`} aria-hidden />
            <span className="text-ink-soft">{status.text}</span>
          </p>
          {isAdmin && (
            <p className="mt-1.5 flex items-center gap-1.5 text-xs text-ok">
              <Lock className="h-3 w-3" aria-hidden /> Administrator mode
            </p>
          )}
        </div>
      </aside>
    </>
  );
}
