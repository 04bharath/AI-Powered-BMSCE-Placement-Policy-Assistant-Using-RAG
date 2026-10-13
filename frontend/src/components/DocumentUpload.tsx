"use client";

import { DragEvent, FormEvent, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  KeyRound,
  Loader2,
  ShieldCheck,
  Trash2,
  Upload,
} from "lucide-react";
import { ApiError, deleteDocument, getDocuments, uploadDocument } from "@/lib/api";
import type { DocumentDetail, DocumentSummary, DocumentsResponse } from "@/types";

interface Props {
  docs: DocumentsResponse | null;
  loading: boolean;
  error: string | null;
  adminToken: string;
  onAdminToken: (token: string) => void;
  onRefresh: (token?: string) => Promise<void>;
  notify: (kind: "success" | "error" | "info", text: string) => void;
}

function isDetail(d: DocumentSummary | DocumentDetail): d is DocumentDetail {
  return "content_hash" in d;
}

const STATUS_STYLE: Record<string, string> = {
  ready: "bg-ok-soft text-ok",
  indexing: "bg-accent-soft text-accent-strong",
  failed: "bg-danger-soft text-danger",
  archived: "bg-canvas text-muted",
};

export default function DocumentUpload({
  docs,
  loading,
  error,
  adminToken,
  onAdminToken,
  onRefresh,
  notify,
}: Props) {
  const [tokenInput, setTokenInput] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const isAdmin = Boolean(adminToken) && docs?.detailed === true;

  const unlock = async (e: FormEvent) => {
    e.preventDefault();
    const t = tokenInput.trim();
    if (!t) return;
    setUnlocking(true);
    try {
      const res = await getDocuments(t);
      if (!res.detailed) throw new ApiError(401, "That token was not accepted.");
      onAdminToken(t);
      setTokenInput("");
      await onRefresh(t);
      notify("success", "Administrator mode enabled for this tab.");
    } catch (err) {
      notify("error", err instanceof ApiError ? err.message : "Could not verify the token.");
    } finally {
      setUnlocking(false);
    }
  };

  const pick = (f: File | undefined | null) => {
    setUploadError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setFile(null);
      setUploadError("Only PDF files can be uploaded.");
      return;
    }
    setFile(f);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0]);
  };

  const upload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const res = await uploadDocument(file, adminToken, documentId);
      notify(res.outcome === "duplicate" ? "info" : "success", res.message);
      setFile(null);
      setDocumentId("");
      if (inputRef.current) inputRef.current.value = "";
      await onRefresh(adminToken);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Upload failed.";
      setUploadError(msg);
      notify("error", msg);
      if (err instanceof ApiError && err.status === 401) onAdminToken("");
      await onRefresh(adminToken);
    } finally {
      setUploading(false);
    }
  };

  const remove = async (id: string) => {
    setDeleting(true);
    try {
      await deleteDocument(id, adminToken);
      notify("success", `Deleted “${id}” and its indexed passages.`);
      setConfirmId(null);
      setConfirmText("");
      await onRefresh(adminToken);
    } catch (err) {
      notify("error", err instanceof ApiError ? err.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  };

  const documents = docs?.documents ?? [];

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-8">
      <div className="mx-auto w-full max-w-4xl space-y-8">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">Policy documents</h1>
          <p className="mt-1 text-muted">
            Only the current version of each document is searched. Older versions are archived and
            never mixed into answers.
          </p>
        </header>

        {!isAdmin ? (
          <form
            onSubmit={unlock}
            className="rounded-2xl border border-line bg-surface p-5 shadow-card"
            aria-labelledby="admin-title"
          >
            <h2 id="admin-title" className="flex items-center gap-2 text-base font-semibold">
              <KeyRound className="h-5 w-5 text-accent" aria-hidden /> Administrator access
            </h2>
            <p className="mt-1 text-sm text-muted">
              Uploading or deleting policies requires the administrator token. It is kept in memory
              for this tab only and is never stored or bundled with the site.
            </p>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <label htmlFor="admin-token" className="sr-only">
                Administrator token
              </label>
              <input
                id="admin-token"
                type="password"
                autoComplete="off"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Administrator token"
                className="flex-1 rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
              <button
                type="submit"
                disabled={!tokenInput.trim() || unlocking}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white hover:bg-ink-soft disabled:opacity-40"
              >
                {unlocking && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Unlock
              </button>
            </div>
          </form>
        ) : (
          <form
            onSubmit={upload}
            className="rounded-2xl border border-line bg-surface p-5 shadow-card"
            aria-labelledby="upload-title"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 id="upload-title" className="flex items-center gap-2 text-base font-semibold">
                <ShieldCheck className="h-5 w-5 text-ok" aria-hidden /> Upload policy or circular
              </h2>
              <button
                type="button"
                onClick={() => {
                  onAdminToken("");
                  void onRefresh("");
                }}
                className="text-sm text-muted underline-offset-2 hover:underline"
              >
                Lock
              </button>
            </div>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={`mt-4 rounded-xl border-2 border-dashed p-6 text-center transition ${
                dragging ? "border-accent bg-accent-soft" : "border-line bg-canvas"
              }`}
            >
              <Upload className="mx-auto h-6 w-6 text-muted" aria-hidden />
              <p className="mt-2 text-sm">
                {file ? (
                  <span className="font-medium">{file.name}</span>
                ) : (
                  <>Drag a PDF here, or </>
                )}{" "}
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="font-medium text-accent-strong underline-offset-2 hover:underline"
                >
                  {file ? "choose another" : "browse"}
                </button>
              </p>
              <label htmlFor="pdf-file" className="sr-only">
                PDF file
              </label>
              <input
                id="pdf-file"
                ref={inputRef}
                type="file"
                accept="application/pdf,.pdf"
                className="sr-only"
                onChange={(e) => pick(e.target.files?.[0])}
              />
            </div>

            <div className="mt-4">
              <label htmlFor="doc-id" className="block text-sm font-medium">
                Document ID <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="doc-id"
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                maxLength={80}
                placeholder="e.g. placement-policy — reuse to publish a new version"
                className="mt-1 w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
              <p className="mt-1 text-xs text-muted">
                Leave blank to derive it from the filename. Uploading changed content under an existing ID
                creates a new version and archives the old one.
              </p>
            </div>

            {uploadError && (
              <p role="alert" className="mt-3 flex items-start gap-2 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {uploadError}
              </p>
            )}

            <button
              type="submit"
              disabled={!file || uploading}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-strong disabled:opacity-40"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Extracting, embedding, indexing…
                </>
              ) : (
                "Upload and index"
              )}
            </button>
          </form>
        )}

        <section aria-label="Indexed documents">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
            {isAdmin ? "All versions" : "Current documents"}
          </h2>

          {loading ? (
            <div className="space-y-3" aria-busy="true">
              <div className="skeleton h-20 w-full" />
              <div className="skeleton h-20 w-full" />
            </div>
          ) : error ? (
            <p role="alert" className="flex items-start gap-2 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {error}
            </p>
          ) : documents.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-line bg-surface p-8 text-center">
              <FileText className="mx-auto h-8 w-8 text-muted" aria-hidden />
              <p className="mt-2 font-medium">No documents indexed yet</p>
              <p className="text-sm text-muted">
                {isAdmin ? "Upload the official placement policy PDF above." : "An administrator needs to upload the policy."}
              </p>
            </div>
          ) : (
            <ul className="space-y-3">
              {documents.map((d) => {
                const detail = isDetail(d) ? d : null;
                const key = `${d.document_id}-${d.version}`;
                return (
                  <li key={key} className="rounded-2xl border border-line bg-surface p-4 shadow-card">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="flex items-center gap-2 font-medium">
                          <FileText className="h-4 w-4 shrink-0 text-muted" aria-hidden />
                          <span className="truncate">{d.filename}</span>
                        </p>
                        <p className="mt-0.5 text-xs text-muted">
                          ID <code className="rounded bg-canvas px-1">{d.document_id}</code> · version {d.version}
                          {d.is_current ? " · current" : ""}
                        </p>
                      </div>
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${STATUS_STYLE[d.status] ?? ""}`}>
                        {d.status === "ready" && <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />}
                        {d.status === "indexing" && <Clock className="h-3.5 w-3.5" aria-hidden />}
                        {d.status === "failed" && <AlertCircle className="h-3.5 w-3.5" aria-hidden />}
                        {d.status}
                      </span>
                    </div>

                    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
                      <div><dt className="text-xs text-muted">Pages</dt><dd>{d.page_count ?? "—"}</dd></div>
                      <div><dt className="text-xs text-muted">Chunks</dt><dd>{d.chunk_count ?? "—"}</dd></div>
                      <div><dt className="text-xs text-muted">Uploaded</dt><dd>{new Date(d.uploaded_at).toLocaleString()}</dd></div>
                      <div><dt className="text-xs text-muted">Updated</dt><dd>{new Date(d.updated_at).toLocaleString()}</dd></div>
                    </dl>

                    {detail?.error && (
                      <p role="alert" className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
                        Indexing error: {detail.error}
                      </p>
                    )}
                    {detail?.warnings?.map((w) => (
                      <p key={w} className="mt-3 rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">{w}</p>
                    ))}

                    {isAdmin && d.is_current && (
                      <div className="mt-3 border-t border-line pt-3">
                        {confirmId === d.document_id ? (
                          <div className="space-y-2">
                            <p className="text-sm">
                              This removes <strong>all versions</strong> of{" "}
                              <code className="rounded bg-canvas px-1">{d.document_id}</code> and its indexed passages.
                              Type the document ID to confirm.
                            </p>
                            <div className="flex flex-col gap-2 sm:flex-row">
                              <label htmlFor={`confirm-${key}`} className="sr-only">Type {d.document_id} to confirm deletion</label>
                              <input
                                id={`confirm-${key}`}
                                value={confirmText}
                                onChange={(e) => setConfirmText(e.target.value)}
                                className="flex-1 rounded-xl border border-line px-3 py-2 text-sm outline-none focus:border-danger focus:ring-2 focus:ring-danger/20"
                              />
                              <button
                                type="button"
                                disabled={confirmText !== d.document_id || deleting}
                                onClick={() => void remove(d.document_id)}
                                className="inline-flex items-center justify-center gap-2 rounded-xl bg-danger px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
                              >
                                {deleting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Delete permanently
                              </button>
                              <button
                                type="button"
                                onClick={() => { setConfirmId(null); setConfirmText(""); }}
                                className="rounded-xl px-4 py-2 text-sm text-muted hover:bg-canvas"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmId(d.document_id)}
                            className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-danger"
                          >
                            <Trash2 className="h-4 w-4" aria-hidden /> Delete document
                          </button>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
