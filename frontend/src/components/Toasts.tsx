"use client";

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import type { Notice } from "@/types";

const STYLES = {
  success: { Icon: CheckCircle2, cls: "border-ok/30 bg-ok-soft text-ok" },
  error: { Icon: AlertCircle, cls: "border-danger/30 bg-danger-soft text-danger" },
  info: { Icon: Info, cls: "border-accent/30 bg-accent-soft text-accent-strong" },
} as const;

export default function Toasts({
  notices,
  onDismiss,
}: {
  notices: Notice[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
    >
      {notices.map((n) => {
        const { Icon, cls } = STYLES[n.kind];
        return (
          <div
            key={n.id}
            role={n.kind === "error" ? "alert" : "status"}
            className={`rise pointer-events-auto flex items-start gap-2.5 rounded-xl border px-3.5 py-3 text-sm shadow-pop ${cls}`}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <p className="flex-1 text-ink">{n.text}</p>
            <button
              type="button"
              onClick={() => onDismiss(n.id)}
              aria-label="Dismiss notification"
              className="rounded p-0.5 text-muted hover:text-ink"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
}
