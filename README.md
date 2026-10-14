<img width="1280" height="1110" alt="BMSCE_Placement_Assistant_Architecture" src="https://github.com/user-attachments/assets/ca17e87b-4d17-4313-977c-ffcbb7b4b40d" /># AI-Powered BMSCE Placement Policy Assistant Using RAG

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

![Uploading<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 1110" width="1280" height="1110" font-family="Inter, Segoe UI, Arial, sans-serif">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#27345a"/></marker>
<style>
.t{font-size:15px;font-weight:600;fill:#0b1b3a}.s{font-size:12px;fill:#5b6478}.h{font-size:13px;font-weight:700;letter-spacing:.08em;fill:#5b6478}
.box{fill:#fff;stroke:#c9cee0;stroke-width:1.5}.acc{fill:#eef0ff;stroke:#4f46e5;stroke-width:1.5}.ext{fill:#fff4e5;stroke:#b45309;stroke-width:1.5}.db{fill:#e6f6f4;stroke:#0f766e;stroke-width:1.5}
.band{fill:none;stroke:#dfe3ef;stroke-width:1.5;stroke-dasharray:5 5}
.ln{stroke:#27345a;stroke-width:1.8;fill:none;marker-end:url(#a)}.bus{stroke:#27345a;stroke-width:1.8;fill:none}
.lbl{font-size:11.5px;fill:#27345a;font-weight:600}
</style></defs>
<rect width="1280" height="1110" fill="#f6f7fb"/>
<text x="40" y="46" font-size="26" font-weight="700" fill="#0b1b3a">AI-Powered BMSCE Placement Policy Assistant Using RAG</text>
<text x="40" y="68" class="s">System architecture · answers to policy questions come from the indexed placement-policy PDF, not from model memory</text>

<!-- BAND 1 -->
<rect x="25" y="95" width="1230" height="620" rx="16" class="band"/>
<text x="45" y="120" class="h">1 · QUESTION ANSWERING (students)</text>

<rect x="40" y="170" width="185" height="80" rx="12" class="box"/><text x="132" y="204" text-anchor="middle" class="t">Student</text><text x="132" y="224" text-anchor="middle" class="s">asks in plain language</text>

<rect x="255" y="130" width="235" height="570" rx="14" class="acc"/>
<text x="372" y="152" text-anchor="middle" class="t" style="font-size:13px">FRONTEND · Next.js</text>
<rect x="275" y="170" width="195" height="80" rx="12" class="box"/><text x="372" y="203" text-anchor="middle" class="t">Chat interface</text><text x="372" y="223" text-anchor="middle" class="s">Markdown answers</text>
<rect x="275" y="275" width="195" height="70" rx="12" class="box"/><text x="372" y="306" text-anchor="middle" class="t">Sidebar / dashboard</text><text x="372" y="326" text-anchor="middle" class="s">status · recent questions</text>

<rect x="510" y="130" width="470" height="570" rx="14" class="acc"/>
<text x="745" y="152" text-anchor="middle" class="t" style="font-size:13px">BACKEND · FastAPI · POST /chat</text>
<rect x="540" y="170" width="410" height="50" rx="12" class="box"/><text x="745" y="200" text-anchor="middle" class="t">Answer router</text>

<rect x="590" y="250" width="360" height="75" rx="12" class="box"/><text x="770" y="276" text-anchor="middle" class="t">Policy route</text><text x="770" y="295" text-anchor="middle" class="s">embed question → top chunks → drop weak matches</text><text x="770" y="312" text-anchor="middle" class="s">no evidence → "contact the placement office"</text>
<rect x="590" y="345" width="360" height="65" rx="12" class="box"/><text x="770" y="374" text-anchor="middle" class="t">General route</text><text x="770" y="393" text-anchor="middle" class="s">greetings and general questions</text>
<rect x="590" y="440" width="360" height="90" rx="12" class="box"/><text x="770" y="470" text-anchor="middle" class="t">Current-information route</text><text x="770" y="490" text-anchor="middle" class="s">optional · only when web search is enabled</text><text x="770" y="507" text-anchor="middle" class="s">never overrides placement-policy rules</text>

<rect x="1030" y="235" width="200" height="80" rx="12" class="db"/><text x="1130" y="265" text-anchor="middle" class="t">ChromaDB</text><text x="1130" y="285" text-anchor="middle" class="s">policy chunks + page metadata</text>
<rect x="1030" y="360" width="200" height="70" rx="12" class="ext"/><text x="1130" y="390" text-anchor="middle" class="t">LLM provider</text><text x="1130" y="410" text-anchor="middle" class="s">Groq / xAI / Ollama / other</text>
<rect x="1030" y="480" width="200" height="80" rx="12" class="ext"/><text x="1130" y="510" text-anchor="middle" class="t">Tavily web search</text><text x="1130" y="530" text-anchor="middle" class="s">optional</text>

<!-- arrows band 1 -->
<path class="ln" d="M225 210 H275"/>
<path class="ln" d="M470 205 H540"/>
<path class="bus" d="M560 220 V485"/>
<path class="ln" d="M560 287 H590"/><path class="ln" d="M560 377 H590"/><path class="ln" d="M560 485 H590"/>
<path class="ln" d="M950 280 H1030"/><text x="960" y="268" class="lbl">retrieve</text>
<path class="ln" d="M950 395 H1030"/><text x="978" y="383" class="lbl">prompt</text>
<path class="ln" d="M1030 520 H950"/><path class="ln" d="M1130 480 V430"/><text x="1140" y="460" class="lbl">results</text>
<path class="ln" d="M1130 315 V360"/><text x="1140" y="343" class="lbl">excerpts</text>

<rect x="590" y="590" width="360" height="90" rx="12" fill="#fff" stroke="#4f46e5" stroke-width="2.5"/>
<text x="770" y="620" text-anchor="middle" class="t">Final answer (output)</text>
<text x="770" y="640" text-anchor="middle" class="s">student-friendly Markdown reply, or the fixed fallback</text>
<text x="770" y="657" text-anchor="middle" class="s">API returns: answer · grounded flag · retrieval details</text>
<path class="ln" d="M1230 395 H1245 V635 H950"/><text x="1000" y="627" class="lbl">generated answer</text>
<path class="ln" d="M590 635 H500 V232 H470"/>
<path class="ln" d="M275 238 H225"/><text x="233" y="262" class="lbl">answer</text>
<text x="272" y="400" class="s" style="display:none"></text>

<g transform="translate(0,130)">
<!-- BAND 2 -->
<rect x="25" y="610" width="1230" height="230" rx="16" class="band"/>
<text x="45" y="635" class="h">2 · DOCUMENT INGESTION (administrator only)</text>
<rect x="40" y="670" width="150" height="100" rx="12" class="box"/><text x="115" y="705" text-anchor="middle" class="t">Administrator</text><text x="115" y="726" text-anchor="middle" class="s">uploads policy PDF</text>
<rect x="215" y="670" width="150" height="100" rx="12" class="acc"/><text x="290" y="705" text-anchor="middle" class="t">Upload page</text><text x="290" y="726" text-anchor="middle" class="s">token kept in memory</text><text x="290" y="743" text-anchor="middle" class="s">Next.js</text>
<rect x="390" y="670" width="150" height="100" rx="12" class="acc"/><text x="465" y="700" text-anchor="middle" class="t">Upload API</text><text x="465" y="721" text-anchor="middle" class="s">upload endpoint</text><text x="465" y="738" text-anchor="middle" class="s">bearer-token check</text>
<rect x="565" y="670" width="150" height="100" rx="12" class="box"/><text x="640" y="700" text-anchor="middle" class="t">Validate + extract</text><text x="640" y="721" text-anchor="middle" class="s">PyMuPDF · per page</text><text x="640" y="738" text-anchor="middle" class="s">duplicate check (hash)</text>
<rect x="740" y="670" width="140" height="100" rx="12" class="box"/><text x="810" y="700" text-anchor="middle" class="t">Chunking</text><text x="810" y="721" text-anchor="middle" class="s">page-aware</text><text x="810" y="738" text-anchor="middle" class="s">800 / 120 overlap</text>
<rect x="905" y="670" width="150" height="100" rx="12" class="box"/><text x="980" y="700" text-anchor="middle" class="t">Embeddings</text><text x="980" y="721" text-anchor="middle" class="s">all-MiniLM-L6-v2</text><text x="980" y="738" text-anchor="middle" class="s">runs locally</text>
<rect x="1080" y="670" width="160" height="100" rx="12" class="db"/><text x="1160" y="700" text-anchor="middle" class="t">Chroma + registry</text><text x="1160" y="721" text-anchor="middle" class="s">new version first,</text><text x="1160" y="738" text-anchor="middle" class="s">old one archived</text>
<path class="ln" d="M190 720 H215"/><path class="ln" d="M365 720 H390"/><path class="ln" d="M540 720 H565"/><path class="ln" d="M715 720 H740"/><path class="ln" d="M880 720 H905"/><path class="ln" d="M1055 720 H1080"/>
<text x="45" y="815" class="s">The chat UI shows only the final answer. Page and source details stay in the API response for auditing.</text>

</g>
<g transform="translate(0,130)">
<!-- Legend -->
<rect x="25" y="865" width="1230" height="85" rx="12" class="box"/>
<text x="45" y="890" class="h">LEGEND</text>
<rect x="45" y="905" width="16" height="16" rx="4" class="acc"/><text x="68" y="918" class="s">Application (frontend / backend)</text>
<rect x="290" y="905" width="16" height="16" rx="4" class="db"/><text x="313" y="918" class="s">Local data store</text>
<rect x="450" y="905" width="16" height="16" rx="4" class="ext"/><text x="473" y="918" class="s">External service (receives question text; keys stay in backend .env)</text>
<rect x="900" y="905" width="16" height="16" rx="4" class="box"/><text x="923" y="918" class="s">Processing step</text>
<rect x="1040" y="905" width="16" height="16" rx="4" fill="#fff" stroke="#4f46e5" stroke-width="2.5"/><text x="1063" y="918" class="s">Final output</text>
</g>
</svg>
 BMSCE_Placement_Assistant_Architecture.svg…]()


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
