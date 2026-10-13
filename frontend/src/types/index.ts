export interface Citation {
  document_id: string;
  filename: string;
  document_version: number;
  page_number: number;
  chunk_id: string;
  excerpt: string;
  distance: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  conversation_id: string;
  grounded: boolean;
  retrieval: Record<string, unknown>;
}

export interface DocumentSummary {
  document_id: string;
  version: number;
  filename: string;
  status: "indexing" | "ready" | "failed" | "archived";
  is_current: boolean;
  page_count: number | null;
  chunk_count: number | null;
  uploaded_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  content_hash: string;
  pages_with_text: number | null;
  error: string | null;
  warnings: string[];
  embedding_model: string | null;
}

export interface DocumentsResponse {
  indexed_documents: number;
  detailed: boolean;
  documents: Array<DocumentSummary | DocumentDetail>;
}

export interface UploadResponse {
  outcome: "indexed" | "duplicate";
  message: string;
  replaced_version: number | null;
  document: DocumentDetail;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  components: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  grounded?: boolean;
  answerSource?: "policy" | "web" | "general" | "none";
  isError?: boolean;
}

export type Notice = { id: number; kind: "success" | "error" | "info"; text: string };
