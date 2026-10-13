# AI-Powered BMSCE Placement Policy Assistant Using RAG

BMSCE Campus is a Retrieval-Augmented Generation (RAG) application for answering student questions about official placement-policy PDFs. It combines local embeddings and ChromaDB with a selectable LLM provider, so placement-rule answers are based on the uploaded policy rather than model memory.

The chat UI intentionally does not show filenames, page references, or source cards. Citation metadata remains available in the backend API for auditing and future UI use.

## What it does

- Validates, extracts, and indexes text-based PDF placement policies page by page.
- Retrieves the most relevant policy excerpts and uses them to answer placement-rule questions.
- Keeps policy questions PDF-only. If the uploaded policy does not contain enough evidence, the assistant asks the student to contact the placement office instead of guessing.
- Answers greetings and ordinary general questions through the configured LLM.
- Optionally uses Tavily web search for current, non-policy information, such as a current placement head, contact details, or news.
- Uses web search before vector retrieval for current-information questions so a broad PDF match on a word such as `placement` does not block a web answer.
- Supports Ollama, Groq, xAI/Grok, and other OpenAI-compatible chat-completions APIs.
- Provides versioned document uploads, duplicate detection, admin-only document management, CORS configuration, and a responsive Next.js interface.

## Important answer-routing rules

| Question type | Answer source |
|---|---|
| Placement eligibility, CGPA, backlogs, offers, internships, or placement rules | Indexed policy PDFs only |
| Greeting or general knowledge question | Configured LLM |
| Current role, contact, news, or BMSCE-specific information | Tavily web search, when enabled |

Web search never overrides placement-policy rules. If no appropriate source is available, the application returns a clear fallback instead of inventing an answer.

## Architecture

```text
Next.js frontend
      |
      v
FastAPI backend
  |-- PDF ingestion -> PyMuPDF -> page-aware chunks -> embeddings -> ChromaDB
  |-- Policy question -> vector retrieval -> selected LLM
  |-- General question -> selected LLM
  `-- Current/non-policy question -> Tavily search -> selected LLM
```

## Project structure

```text
placement-policy-rag/
├── frontend/                    Next.js + TypeScript + Tailwind
│   └── src/
│       ├── app/                 Pages and layout
│       ├── components/          Chat, sidebar, and document UI
│       ├── lib/                 API client
│       └── types/               Shared frontend types
├── backend/
│   ├── app.py                   FastAPI application and routes
│   ├── config.py                Environment-based settings
│   ├── src/
│   │   ├── document_loader.py   PDF validation and extraction
│   │   ├── chunking.py          Page-aware chunking
│   │   ├── embeddings.py        Sentence Transformers adapter
│   │   ├── vector_store.py      ChromaDB and document registry
│   │   ├── retriever.py         Retrieval and optional reranking
│   │   ├── llm.py               LLM providers and prompts
│   │   ├── web_search.py        Optional Tavily search adapter
│   │   └── rag_pipeline.py      Answer routing and orchestration
│   └── tests/                   Unit and API tests
└── data/                        Private PDFs (git-ignored)
```

## Requirements

- Python 3.11+
- Node.js 20+
- An LLM provider: Ollama, Groq, xAI, or an OpenAI-compatible API
- A Tavily API key only when web search is enabled

## Quick start

### 1. Configure and start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app:app --reload --port 8000
```

Set the LLM and admin values in `backend/.env` before starting. Keep real credentials in `.env` only; never commit them or expose them through `NEXT_PUBLIC_*` variables.

### 2. Start the frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Configuration

All backend settings are read from `backend/.env`.

### LLM providers

```env
# Ollama (local)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
```

```env
# Groq
LLM_PROVIDER=groq
LLM_MODEL=your-groq-model-id
LLM_API_KEY=your-groq-api-key
```

```env
# xAI / Grok
LLM_PROVIDER=xai
LLM_MODEL=your-grok-model-id
LLM_API_KEY=your-xai-api-key
```

The provider value for Grok is `xai`, not `grok`. Groq and Grok/xAI are separate services.

For another OpenAI-compatible provider:

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://provider.example/v1
LLM_MODEL=your-model-id
LLM_API_KEY=your-api-key
```

### Optional web search

Enable this to answer current, non-policy questions such as “Who is our placement head?”

```env
ENABLE_WEB_SEARCH=true
TAVILY_API_KEY=your-tavily-api-key
WEB_SEARCH_MAX_RESULTS=4
WEB_SEARCH_TIMEOUT_SECONDS=15
```

Restart the backend after changing `.env`. The `/health` endpoint reports whether web search is enabled and whether a key is configured; it never returns the key itself.

### Other useful settings

| Variable | Default | Purpose |
|---|---:|---|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `CHROMA_PERSIST_DIR` | `./.chroma` | Persistent vector-store directory |
| `CHROMA_COLLECTION` | `placement_policy` | Chroma collection name |
| `RETRIEVAL_TOP_K` | `3` | Number of relevant chunks retained |
| `RETRIEVAL_FETCH_K` | `6` | Candidates fetched before filtering/reranking |
| `RETRIEVAL_MAX_DISTANCE` | `0.75` | Maximum cosine distance for a relevant match |
| `ADMIN_API_TOKEN` | *(empty)* | Required bearer token for upload and delete operations |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |

Changing `EMBEDDING_MODEL` for an existing collection is intentionally blocked. Use a new collection/directory and re-index the PDFs.

## API

Interactive API documentation is available at `http://localhost:8000/docs`.

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /health` | none | Service and component status |
| `GET /documents` | optional admin token | Lists indexed documents; admin access includes detail |
| `POST /documents/upload` | admin token | Uploads and indexes a PDF |
| `DELETE /documents/{id}?confirm={id}` | admin token | Removes a document and its vectors |
| `POST /chat` | none | Sends a question and receives an answer, grounding state, and retrieval metadata |

Admin calls require `Authorization: Bearer <ADMIN_API_TOKEN>`.

## Testing

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm.cmd run typecheck
npm.cmd run build
```

The standard tests use deterministic fake embeddings, LLMs, and web-search results. Integration tests marked `integration` require the configured live services.

## Privacy and deployment notes

- With local Ollama and web search disabled, policy questions and their retrieved excerpts remain on the machine running the backend.
- With Groq, xAI, or another cloud LLM, the relevant prompt content is sent to that provider.
- With web search enabled, non-policy/current-information queries are sent to Tavily. Do not enable it if that data flow is not appropriate for your deployment.
- Embeddings and ChromaDB remain local unless you deploy them elsewhere.
- Use HTTPS, a strong `ADMIN_API_TOKEN`, a persistent volume for `.chroma`, and a single backend worker. The JSON registry is not designed for multi-worker writes.

## Limitations

- Image-only/scanned PDFs require OCR and are currently rejected.
- PDF tables and multi-column layouts may extract imperfectly.
- Web results can be stale or incomplete; current facts should be verified on official BMSCE pages.
- The chat has no authenticated student accounts or rate limiting.
- Conversation IDs are echoed for the client, but follow-up questions are retrieved independently.
