"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, GraduationCap, ShieldAlert, User } from "lucide-react";
import type { Message } from "@/types";

export default function ChatMessage({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="rise flex justify-end gap-3">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-accent px-4 py-3 text-[0.95rem] leading-relaxed text-white shadow-card">
          <span className="sr-only">You: </span>
          {message.content}
        </div>
        <div className="mt-1 hidden h-8 w-8 shrink-0 place-items-center rounded-full bg-ink text-white sm:grid" aria-hidden>
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="rise flex gap-3">
      <div className="mt-1 hidden h-8 w-8 shrink-0 place-items-center rounded-full bg-accent-soft text-accent-strong sm:grid" aria-hidden>
        <GraduationCap className="h-4 w-4" />
      </div>
      <div className="min-w-0 max-w-[92%] flex-1">
        <div
          className={`rounded-2xl rounded-tl-md border p-4 shadow-card ${
            message.isError ? "border-danger/30 bg-danger-soft" : "border-line bg-surface"
          }`}
        >
          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
            {message.isError ? (
              <>
                <AlertTriangle className="h-3.5 w-3.5 text-danger" aria-hidden /> Couldn’t get an answer
              </>
            ) : (
              <>
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent" aria-hidden /> AI explanation
              </>
            )}
          </p>
          <div className="md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>

          {!message.isError && (message.answerSource === "none" || (!message.answerSource && message.grounded === false)) && (
            <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-warn-soft px-3 py-2 text-xs text-warn">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              No verified information was available. Please confirm with the placement office or official BMSCE website.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
