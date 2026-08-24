# L2 SDS Intelligence — System Architecture Specification

---

## 1. Executive Summary

**L2 SDS Intelligence** is an agentic AI platform for chemical Safety Data Sheet (SDS) discovery, retrieval, and multi-stage verification. It pairs dynamic **LangGraph action selection** with an **independent reflection/verification stage**, **SSRF-safe streaming document fetching**, **strict Pydantic structured output validation**, and a **FastMCP Excel storage transport boundary**.

The system prevents hallucinations by enforcing a strict **"Retrieval Before Generation"** invariant: compliance decisions are derived strictly from raw text extracted from real manufacturer PDF documents rather than generative synthesis.

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
│         (/api/sds/search, /api/health, /api/stats, /api/history, /api/batch/*)  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Async Ainvoke
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LangGraph StateGraph Agent Engine                        │
│                                                                                 │
│   ┌──────────────────┐      ┌─────────────┐      ┌──────────────┐              │
│   │  decide_action   │ ───► │ search_node │ ───► │  rank_node   │              │
│   └────────┬─────────┘      └─────────────┘      └──────┬───────┘              │
│            ▲                                            │                      │
│            │           ┌────────────────────────────────┘                      │
│            │           ▼                                                       │
│            │    ┌──────────────┐      ┌─────────────────┐                      │
│            └─── │  fetch_node  │ ───► │  draft_decision │                      │
│                 └──────────────┘      └────────┬────────┘                      │
│                                                │                               │
│                                                ▼                               │
│                                     ┌─────────────────────┐                    │
│                                     │  verify_decision    │                    │
│                                     │(Independent Review) │                    │
│                                     └──────────┬──────────┘                    │
│                                                │                               │
│                     ┌──────────────────────────┴──────────────────────────┐    │
│                     ▼                                                     ▼    │
│            ┌─────────────────┐                                  ┌────────────┐ │
│            │    corrective   │                                  │extract_    │ │
│            │    action_node  │ ───► [extract_final_node] ───►   │final_node  │ │
│            └─────────────────┘                                  └─────┬──────┘ │
└───────────────────────────────────────────────────────────────────────┼────────┘
                                                                        │ Verified Result
                                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FastMCP Excel Transport Boundary                        │
│             (sample_requests_eval.xlsx & logs/agent_trace.jsonl)                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Architectural Components

### 3.1 Dynamic Action Selection (`src/workflow.py`)
* The agent evaluates current state, prerequisites, previous observations, and action history to dynamically select discrete actions:
  - `SEARCH`: Formulates structured search queries combining chemical name, manufacturer, part number, and jurisdiction.
  - `RANK`: Evaluates and scores discovered candidate URLs using deterministic multi-factor heuristics (0–100).
  - `FETCH`: Safely downloads document streams with SSRF validation, redirect checks, and stream size caps.
  - `DRAFT`: Synthesizes gathered evidence into a preliminary draft verdict.
  - `VERIFY`: Executes independent reflection/verification over the draft and evidence.
  - `RETRY`: Selects alternative candidate URLs if verification reveals insufficient evidence.
  - `FINISH`: Validates final output with strict Pydantic schemas.

### 3.2 Independent Reflection & Verification Stage
* Programmatically and semantically cross-checks draft decisions:
  - **Grounding Validation**: Enforces invariant `final_url in discovered_candidates AND final_url in successful_fetches`.
  - **Authenticity Check**: Verifies presence of genuine GHS/OSHA SDS headers.
  - **Manufacturer Match**: Detects manufacturer discrepancies and downgrades `EXACT MATCH` -> `BEST AVAILABLE` or `NEEDS REVIEW`.
  - **Product Match**: Verifies chemical identity tokens against document text.
  - **Part Number & CAS Match**: Confirms catalog numbers and CAS registry identifiers.
  - **Confidence Calibration**: Ensures confidence is bounded (`0 <= confidence <= 100`) and justified by evidence.

### 3.3 SSRF & Network Safety Layer (`src/security.py`)
* **Scheme Restriction**: Strictly `http` and `https` allowed; blocks `file://`, `ftp://`, `gopher://`, etc.
* **IP Filtering**: DNS resolution verifies that resolved IP addresses do not belong to loopback (`127.0.0.0/8`, `::1`), private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), or cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
* **Redirect Safety**: Intercepts redirect hops and re-validates each target URL against SSRF policy before connection.
* **Stream Bounds**: Reads downloads in 64KB chunks up to a strict 10MB maximum limit.

### 3.4 Multi-Page SDS Parser & Normalization (`src/sds_parser.py`)
* Reads first 6 pages of binary PDF documents using `PyMuPDF (fitz)` or full visible HTML structures via `BeautifulSoup4`.
* Extracts standard 16 GHS/OSHA sections, CAS numbers (`\b\d{2,7}-\d{2}-\d\b`), catalog/part numbers, revision dates, and language/jurisdiction markers.

### 3.5 FastMCP Excel Storage Transport (`src/mcp_server.py` & `src/mcp_client.py`)
* Exposes standard MCP tools over `stdio` transport using `FastMCP`:
  - `get_pending_requests`: Reads target rows from Excel workbooks with automated sheet classification and column mapping.
  - `update_request_status`: Writes verified status, confirmed URL, confidence score, and reasoning back into Excel in-place.
* **Intentional Hybrid Architecture**: Excel persistence is isolated across the MCP transport boundary, while search, rank, fetch, and parser tools remain LangGraph-native for tight observation streaming and performance.

### 3.6 Isolated Batch Job Management (`server.py`)
* Replaces unsafe process-global mutable state with a thread-safe `BatchJobManager` tracking isolated jobs by `job_id` with asyncio locks.
