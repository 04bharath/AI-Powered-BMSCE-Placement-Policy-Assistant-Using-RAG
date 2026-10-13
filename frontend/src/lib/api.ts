import type {
  ChatResponse,
  DocumentsResponse,
  HealthResponse,
  UploadResponse,
} from "@/types";

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function detailToText(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc, msg, ...}]
    return detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : ""))
      .filter(Boolean)
      .join("; ");
  }
  return null;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the BMSCE Campus server. Check that the backend is running.");
  }

  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      message = detailToText(body?.detail) ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  return (await res.json()) as T;
}

export const getHealth = () => request<HealthResponse>("/health");

export const getDocuments = (token?: string) =>
  request<DocumentsResponse>("/documents", { cache: "no-store" }, token);

export const sendChat = (question: string, conversationId?: string) =>
  request<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId ?? null }),
  });

export function uploadDocument(file: File, token: string, documentId?: string) {
  const form = new FormData();
  form.append("file", file);
  if (documentId?.trim()) form.append("document_id", documentId.trim());
  return request<UploadResponse>("/documents/upload", { method: "POST", body: form }, token);
}

export const deleteDocument = (documentId: string, token: string) =>
  request<{ deleted: string }>(
    `/documents/${encodeURIComponent(documentId)}?confirm=${encodeURIComponent(documentId)}`,
    { method: "DELETE" },
    token,
  );
