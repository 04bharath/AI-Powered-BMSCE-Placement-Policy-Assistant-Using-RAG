"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import ChatInterface from "@/components/ChatInterface";
import DocumentUpload from "@/components/DocumentUpload";
import Sidebar, { type View } from "@/components/Sidebar";
import Toasts from "@/components/Toasts";
import { ApiError, getDocuments, sendChat } from "@/lib/api";
import type { DocumentsResponse, Message, Notice } from "@/types";

const RECENT_KEY = "campuscompass.recent";
const MAX_RECENT = 6;

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [menuOpen, setMenuOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [recent, setRecent] = useState<string[]>([]);

  const [docs, setDocs] = useState<DocumentsResponse | null>(null);
  const [docsLoading, setDocsLoading] = useState(true);
  const [docsError, setDocsError] = useState<string | null>(null);

  // Held in memory only: never persisted, never in the bundle.
  const [adminToken, setAdminToken] = useState("");
  const [notices, setNotices] = useState<Notice[]>([]);
  const noticeId = useRef(0);

  const notify = useCallback((kind: Notice["kind"], text: string) => {
    const id = ++noticeId.current;
    setNotices((n) => [...n, { id, kind, text }]);
    window.setTimeout(() => setNotices((n) => n.filter((x) => x.id !== id)), kind === "error" ? 8000 : 5000);
  }, []);

  const refreshDocs = useCallback(async (token?: string) => {
    setDocsLoading(true);
    try {
      setDocs(await getDocuments(token || undefined));
      setDocsError(null);
    } catch (err) {
      setDocs(null);
      setDocsError(err instanceof ApiError ? err.message : "Could not load documents.");
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshDocs();
    try {
      const raw = window.localStorage.getItem(RECENT_KEY);
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      if (Array.isArray(parsed)) setRecent(parsed.filter((q): q is string => typeof q === "string").slice(0, MAX_RECENT));
    } catch {
      /* storage unavailable or corrupt: start empty */
    }
  }, [refreshDocs]);

  const remember = (q: string) => {
    setRecent((prev) => {
      const next = [q, ...prev.filter((x) => x !== q)].slice(0, MAX_RECENT);
      try {
        window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const ask = useCallback(
    async (question: string) => {
      if (loading) return;
      setView("chat");
      remember(question);
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", content: question }]);
      setLoading(true);
      try {
        const res = await sendChat(question, conversationId);
        setConversationId(res.conversation_id);
        const answerSource = res.retrieval.answer_source;
        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: res.answer,
            citations: res.citations,
            grounded: res.grounded,
            answerSource:
              answerSource === "policy" || answerSource === "web" ||
              answerSource === "general" || answerSource === "none"
                ? answerSource
                : undefined,
          },
        ]);
      } catch (err) {
        const text = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
        setMessages((m) => [
          ...m,
          { id: crypto.randomUUID(), role: "assistant", content: text, isError: true },
        ]);
        notify("error", text);
      } finally {
        setLoading(false);
      }
    },
    [loading, conversationId, notify],
  );

  const clear = () => {
    setMessages([]);
    setConversationId(undefined);
    notify("info", "Conversation cleared.");
  };

  const isAdmin = Boolean(adminToken) && docs?.detailed === true;

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar
        view={view}
        onViewChange={setView}
        recent={recent}
        onAsk={(q) => void ask(q)}
        docs={docs}
        docsLoading={docsLoading}
        docsError={docsError}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        isAdmin={isAdmin}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3 lg:hidden">
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            className="rounded-lg p-2 text-ink hover:bg-canvas"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          <span className="font-semibold tracking-tight">BMSCE Campus</span>
        </header>

        <main id="main" className="min-h-0 flex-1">
          {view === "chat" ? (
            <ChatInterface
              messages={messages}
              loading={loading}
              onSend={(q) => void ask(q)}
              onClear={clear}
              docs={docs}
              docsLoading={docsLoading}
              docsError={docsError}
              recent={recent}
            />
          ) : (
            <DocumentUpload
              docs={docs}
              loading={docsLoading}
              error={docsError}
              adminToken={adminToken}
              onAdminToken={setAdminToken}
              onRefresh={refreshDocs}
              notify={notify}
            />
          )}
        </main>
      </div>

      <Toasts notices={notices} onDismiss={(id) => setNotices((n) => n.filter((x) => x.id !== id))} />
    </div>
  );
}
