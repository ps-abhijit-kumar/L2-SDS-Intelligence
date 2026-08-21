# L2 SDS Intelligence — System Architecture Specification

---

## 1. Executive Summary

**L2 SDS Intelligence** is a production-grade, AI-powered Safety Data Sheet (SDS) discovery, verification, and intelligence platform. It automates chemical compliance retrieval by pairing a deterministic search and ranking pipeline with a cyclic **LangGraph ReAct agent**, **FastMCP Excel storage integration**, and **Groq Cloud LLM semantic validation**.

The system prevents hallucinations by enforcing a **"Retrieval Before Generation"** philosophy: compliance decisions are derived strictly from raw text extracted from real manufacturer PDF documents rather than generative synthesis.

---

## 2. End-to-End System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           React + TypeScript Frontend                           │
│     (Vite + Tailwind CSS + TanStack Query + Recharts + Lucide Enterprise UI)     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTP REST / JSON
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Backend Layer                              │
│         (/api/sds/search, /api/health, /api/stats, /api/history, /api/review)   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Async Ainvoke
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LangGraph StateGraph Agent Engine                        │
│                       (Cyclic ReAct State Machine Node)                         │
└────────────┬───────────────────────────┬───────────────────────────┬────────────┘
             │ Tool Call                 │ Tool Call                 │ Tool Call
             ▼                           ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│    search_duckduckgo    │ │   rank_sds_candidates   │ │   fetch_document_text   │
│  (ddgs Search Provider) │ │ (Utility Ranker 0-100)  │ │ (PyMuPDF fitz Extractor)│
└─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         │ Document Text Evidence & Prompt State
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Groq Cloud LLM Validation                             │
│                  (openai/gpt-oss-120b Function Calling Node)                   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Pydantic SDSValidationResult
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FastMCP Excel Server & Audit                          │
│               (sample_requests_eval.xlsx & logs/agent_trace.jsonl)              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Component Breakdown

### 3.1 Frontend Command Center (`frontend/`)
* **Framework**: React 18 with TypeScript and Vite.
* **State Management**: TanStack React Query v5 for asynchronous query caching, background polling, and optimistic cache invalidation.
* **Design System**: Tailored dark command-center aesthetic (`#070A12` base, electric cyan accents, glassmorphic panels, glowing status badges).
* **Key Workspaces**:
  1. **Executive Dashboard**: Real-time KPI telemetry, subsystem operational health, verdict distribution charts, and recent activity logs.
  2. **SDS Verification Console**: Chemical search form with preset shortcuts, live execution progress timeline, structured decision cards, and document preview modals.
  3. **Verification Audit History**: Searchable and filterable table reading directly from `logs/agent_trace.jsonl` with deep LangGraph message trace inspection.
  4. **Human Review Queue**: Focused compliance view for results flagged as `NEEDS REVIEW`.
  5. **Agent Trace Explorer**: Interactive visualization of the LangGraph state machine with step-by-step tool invocation payloads.
  6. **System Settings**: Model parameters, recursion limits, and environment diagnostics.

### 3.2 Backend REST Layer (`server.py`)
* Built with **FastAPI** and **Uvicorn**, providing CORS-enabled REST endpoints:
  * `GET /api/health`: Real telemetry for LangGraph agent, Groq configuration, FastMCP server, and Excel database.
  * `POST /api/sds/search`: Asynchronously invokes `create_sds_graph().ainvoke(...)`, logs execution traces to `logs/agent_trace.jsonl`, and returns verified results.
  * `GET /api/history`: Returns audit records with keyword filtering, status filtering, and pagination.
  * `GET /api/history/{id}`: Returns deep trace records by ID.
  * `GET /api/stats`: Computes actual aggregate KPI metrics (total verifications, exact matches, resolution rate, average confidence).
  * `GET /api/review`: Filters records flagged for human review.
  * `GET /api/trace/latest`: Returns the most recent execution message sequence.

### 3.3 LangGraph ReAct Agent Engine (`src/workflow.py`)
* Orchestrates agent execution using `langgraph.graph.StateGraph` and `langgraph.graph.MessagesState`.
* **State Tracking (`src/state.py`)**:
  * `messages`: Chronological array of interaction messages (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`).
  * `row_data`: Target request attributes (Product Name, Manufacturer Company, Jurisdiction, Language).
  * `final_status`: Final verification verdict (`EXACT MATCH`, `BEST AVAILABLE`, `NEEDS REVIEW`, `ERROR`).
  * `final_url`: Confirmed direct URL to the Safety Data Sheet document.
  * `confidence`: Computed utility ranking score (0–100).
  * `detailed_reasoning`: LLM-generated compliance rationale explaining document validation.
* **Control Flow**:
  1. Formulates structured search queries combining product name, manufacturer, jurisdiction, and `"SDS PDF"`.
  2. Calls `search_duckduckgo` to retrieve candidate links and snippets.
  3. Evaluates and scores candidate URLs using `rank_sds_candidates`.
  4. Downloads and extracts document text using `fetch_document_text`.
  5. Cross-checks evidence using Groq Cloud LLM function calling.
  6. Enforces recursion limits (`recursion_limit=15`) to prevent infinite reasoning loops.

### 3.4 Deterministic SDS Discovery & Extraction Tools (`src/tools.py`)
* `search_duckduckgo`: Rate-limit-free web discovery tailored for official chemical safety data repositories.
* `rank_sds_candidates`: Deterministic heuristic scoring engine (0–100) prioritizing official manufacturer domains, PDF document extensions, and product/company keyword matches.
* `fetch_document_text`: Downloads target document streams, parses binary PDF pages using `PyMuPDF (fitz)` or HTML structures via `BeautifulSoup4`, and extracts safety text snippets.

### 3.5 Model Context Protocol (MCP) Integration (`src/mcp_server.py` & `src/mcp_client.py`)
* Exposes standard MCP tools over `stdio` transport using `FastMCP`:
  * `get_pending_requests`: Reads target rows from `sample_requests_eval.xlsx`, automatically skipping already resolved rows.
  * `update_request_status`: Writes verified status, confirmed URL, confidence score, and reasoning back into Excel in-place.
* The Excel database functions as persistent, auditable memory for batch evaluations.

---

## 4. SDS Lifecycle & Decision Flow

```text
Incoming Chemical Request
   │
   ▼
[ 1. Query Formulation ] ──► Injects product name, manufacturer, jurisdiction, and "SDS PDF"
   │
   ▼
[ 2. Autonomous Discovery ] ──► search_duckduckgo returns raw candidate URLs & snippets
   │
   ▼
[ 3. Deterministic Utility Ranking ] ──► rank_sds_candidates scores URLs (0-100)
   │
   ▼
[ 4. Document Fetch & Extraction ] ──► fetch_document_text extracts raw PDF text via PyMuPDF
   │
   ▼
[ 5. LLM Semantic Validation ] ──► Groq Cloud LLM checks manufacturer match, product, & GHS elements
   │
   ▼
[ 6. Schema Extraction & Sanity Check ] ──► URL validation, placeholder downgrade & final state
   │
   ├── Confidence >= 80% & Manufacturer Verified ──► EXACT MATCH
   ├── Minor Jurisdiction / Variant Match         ──► BEST AVAILABLE
   └── Low Confidence / Unverified Supplier       ──► NEEDS REVIEW (Routed to Human Queue)
```

---

## 5. Security & Credential Isolation

1. **Zero Secret Leakage**: `GROQ_API_KEY` is strictly confined to the backend server environment and is never bundled into client-side JavaScript or returned in API responses.
2. **CORS Isolation**: The FastAPI backend restricts access to authorized frontend origins.
3. **Audit Immutability**: Real agent execution steps and tool payloads are persisted to `logs/agent_trace.jsonl` for compliance audits.
