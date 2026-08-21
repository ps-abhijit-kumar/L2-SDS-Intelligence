# L2 SDS Intelligence

<div align="center">

**Enterprise AI Command Center for Autonomous Safety Data Sheet Discovery, Batch Verification & Intelligence**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.3-cyan.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-ReAct%20Agent-purple.svg)](https://www.langchain.com/langgraph)
[![FastMCP](https://img.shields.io/badge/MCP-Standard%20Protocol-green.svg)](https://github.com/jlowin/fastmcp)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-Command%20Center%20Dark-38bdf8.svg)](https://tailwindcss.com/)

</div>

---

## 🌟 What is L2 SDS Intelligence?

Chemical Safety Data Sheets (SDS) are distributed across fragmented manufacturer portals, regulatory repositories, and distributor databases. Locating, verifying, and validating the exact SDS for a specific product, manufacturer, jurisdiction, and language is a slow, manual, and error-prone process.

**L2 SDS Intelligence** is a production-grade, AI-powered Safety Data Sheet discovery, verification, and intelligence platform. It automates chemical compliance retrieval with a complete end-to-end batch and single-query workflow:

```text
Excel SDS Request File (sample_requests_eval.xlsx)
        ↓
FastMCP Server reads pending request rows
        ↓
Extracts Product / Manufacturer / Country / Language
        ↓
Autonomous DuckDuckGo chemical candidate discovery
        ↓
Deterministic candidate ranking (0–100 utility score)
        ↓
PyMuPDF (fitz) binary document stream text extraction
        ↓
Groq Cloud LLM (openai/gpt-oss-120b) semantic validation
        ↓
Verdict: EXACT MATCH / BEST AVAILABLE / NEEDS REVIEW / ERROR
        ↓
FastMCP writes Found URL, Status, Confidence, Reasoning back to Excel
        ↓
Interactive Web Command Center & Live Batch Progress
        ↓
Human Review Queue & Instant Excel Export
```

> **Retrieval Before Generation**: L2 never hallucinates compliance data. All verdicts are derived exclusively from actual manufacturer PDF document text.

---

## 🚀 Key Capabilities

* **Primary Excel Batch Processing**: Upload any custom `.xlsx` chemical request sheet or select the built-in benchmark (`sample_requests_eval.xlsx`).
* **FastMCP Persistent Storage**: Standardized Model Context Protocol (MCP) server managing persistent Excel reads and in-place updates.
* **Autonomous SDS Discovery**: Targeted search queries formulated to locate official manufacturer Safety Data Sheets.
* **Deterministic Utility Ranking (0–100)**: Proprietary heuristic scoring engine prioritizing credible manufacturer domains, exact chemical matches, and PDF extensions.
* **PyMuPDF Document Extraction**: In-memory binary PDF stream reader extracting authentic safety text from candidate documents.
* **Semantic LLM Validation**: Groq-powered reasoning (`openai/gpt-oss-120b`) cross-checking chemical name, manufacturer identity, and language against OSHA/GHS standards.
* **Structured Verification Decisions**:
  * `EXACT MATCH`: High confidence (≥80%) with verified manufacturer and chemical specification.
  * `BEST AVAILABLE`: Valid safety document with minor variant or jurisdiction difference.
  * `NEEDS REVIEW`: Flagged for human compliance review due to ambiguous supplier match or low confidence.
* **Human-in-the-Loop Review Queue**: Dedicated workspace for safety officers to inspect candidate documents, confidence scores, and agent reasoning.
* **Immutable Audit Trail**: Chronological execution logs recorded directly to `logs/agent_trace.jsonl`.
* **Interactive Agent Trace Explorer**: Step-by-step visual inspection of the LangGraph state machine and tool invocation arguments.

---

## 🏛️ Architecture

```text
┌────────────────────────────────────────────────────────┐
│             React + TypeScript Frontend                │
│   (Vite + Tailwind CSS + TanStack Query + Recharts)    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP REST / JSON
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend                      │
│        (/api/batch/*, /api/sds/search, /api/health)    │
└───────────────────────────┬────────────────────────────┘
                            │ Async Ainvoke
                            ▼
┌────────────────────────────────────────────────────────┐
│               LangGraph ReAct SDS Agent                │
│    (DuckDuckGo -> Utility Ranker -> PyMuPDF Reader)    │
└───────────────────────────┬────────────────────────────┘
                            │ Tool Calling
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Groq Cloud LLM API                     │
│                (openai/gpt-oss-120b)                   │
└───────────────────────────┬────────────────────────────┘
                            │ Structured Decision
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastMCP Protocol Server                  │
│       (sample_requests_eval.xlsx & Audit Logs)         │
└────────────────────────────────────────────────────────┘
```

---

## 📊 Excel Input & Output Schema

The platform accepts and updates Excel spreadsheets with the following schema:

| Column Header | Type | Role | Description |
| :--- | :--- | :--- | :--- |
| `S.No.` | Integer | Input | Sequence number |
| `Product` | Text | Input | Chemical substance name (e.g. *Acetone*) |
| `Product Name` | Text | Input | Full product specification (e.g. *Acetone Solution*) |
| `Product Company Name` | Text | Input | Target manufacturer / supplier (e.g. *Sigma-Aldrich*) |
| `Language` | Text | Input | Target SDS document language (e.g. *English*) |
| `Country` | Text | Input | Target jurisdiction (e.g. *United States*) |
| `Found URL` | Text (URL) | **Output** | Confirmed link to the verified Safety Data Sheet |
| `Status` | Text | **Output** | `EXACT MATCH` \| `BEST AVAILABLE` \| `NEEDS REVIEW` \| `ERROR` |
| `Confidence` | Integer | **Output** | Heuristic utility score (0–100) |
| `Reasoning` | Text | **Output** | LLM validation rationale citing extracted evidence |

---

## 📂 Project Structure

```text
C:\Coding\Projects\L2
├── docs/                       # Architecture & technical documentation
│   └── ARCHITECTURE.md         # Comprehensive system specification
├── frontend/                   # React 18 + Vite + Tailwind frontend application
│   ├── public/                 # Static assets & SVG favicon
│   ├── src/
│   │   ├── components/         # UI & Domain components
│   │   │   ├── batch/          # Batch upload, progress monitor, and preview tables
│   │   │   ├── common/         # Atomic primitives (Card, Button, Input, StatusBadge, etc.)
│   │   │   ├── dashboard/      # KPI Grid, Telemetry Cards, Distribution Charts
│   │   │   ├── history/        # Audit Tables, Search/Filter Bars, Trace Modal
│   │   │   ├── review/         # Human-in-the-Loop compliance queue & inspection drawer
│   │   │   ├── search/         # Single AI Search Console, Timeline, Result Card
│   │   │   └── trace/          # LangGraph state machine diagram & message inspector
│   │   ├── hooks/              # Custom React Query data fetching hooks (useBatch, useStats, etc.)
│   │   ├── layouts/            # Command center shell (MainLayout, Sidebar, Header)
│   │   ├── pages/              # Primary route views (Dashboard, BatchProcessing, Search, etc.)
│   │   ├── services/           # Typed REST API client (api.ts)
│   │   ├── types/              # TypeScript interfaces (sds.ts)
│   │   ├── utils/              # Class merging, formatters, and status tokens
│   │   ├── App.tsx             # Root router & QueryClientProvider
│   │   └── main.tsx            # React application mount
│   ├── package.json            # Frontend dependencies & build scripts
│   ├── tailwind.config.js      # Command center dark theme tokens & glows
│   └── vite.config.ts          # Build config with /api -> http://127.0.0.1:8000 proxy
├── logs/                       # Application runtime audit logs
│   └── agent_trace.jsonl       # Persistent JSONL trace logs
├── src/                        # Core Python agent & MCP implementation
│   ├── mcp_client.py           # FastMCP stdio client wrapper
│   ├── mcp_server.py           # FastMCP server interacting with Excel
│   ├── schema.py               # Pydantic schemas (SDSValidationResult)
│   ├── state.py                # LangGraph MessagesState & SDSState definitions
│   ├── tools.py                # DuckDuckGo search, Utility Ranker, PyMuPDF extractor
│   └── workflow.py             # LangGraph ReAct StateGraph agent definition
├── tests/                      # Pytest unit & integration test suites
│   ├── test_mcp_client.py      # MCP client tests
│   ├── test_server_batch.py    # Batch API tests
│   ├── test_tools.py           # Search, ranking, & extraction tool tests
│   └── test_workflow.py        # LangGraph workflow tests
├── .env.example                # Root backend environment template
├── .gitignore                  # Comprehensive Git exclusion policy
├── evaluate.py                 # Batch evaluation script for Excel benchmarks
├── main.py                     # CLI batch runner for SDS processing
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
├── sample_requests_eval.xlsx   # Benchmark evaluation Excel database
├── server.py                   # FastAPI REST backend server
└── README.md                   # Project documentation
```

---

## ⚙️ Prerequisites

* **Python**: `v3.10` or higher (tested on Python 3.13)
* **Node.js**: `v18.0.0` or higher
* **npm**: `v9.0.0` or higher
* **Groq Cloud API Key**: Obtain a free API key from [Groq Console](https://console.groq.com/keys).

---

## 🚀 Quickstart & Setup Guide

### 1. Backend Setup

```bash
# 1. Navigate to project root:
cd C:\Coding\Projects\L2

# 2. Create and activate a Python virtual environment:
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell
# source .venv/bin/activate    # On Linux/macOS

# 3. Install backend dependencies:
pip install -r requirements.txt

# 4. Configure environment variables:
cp .env.example .env
```

Open `.env` and add your Groq API key:
```ini
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
EXCEL_FILE_PATH=sample_requests_eval.xlsx
```

```bash
# 5. Start the FastAPI backend server:
python server.py
```
*The backend API will start at `http://127.0.0.1:8000`.*

---

### 2. Frontend Setup

In a separate terminal window:

```bash
# 1. Navigate to the frontend directory:
cd C:\Coding\Projects\L2\frontend

# 2. Install frontend dependencies:
npm install

# 3. Configure frontend environment (defaults to proxying /api):
cp .env.example .env

# 4. Start the Vite development server:
npm run dev
```
*The web command center will be live at `http://127.0.0.1:5173`.*

---

## 🌐 Application URLs

| Service | URL | Description |
| :--- | :--- | :--- |
| **Frontend Command Center** | `http://127.0.0.1:5173` | Interactive React web interface |
| **FastAPI Backend Server** | `http://127.0.0.1:8000` | REST API layer |
| **Interactive API Docs (Swagger)** | `http://127.0.0.1:8000/docs` | OpenAPI specification |

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Subsystem telemetry (LangGraph, Groq, FastMCP, Excel DB) |
| `GET` | `/api/batch/preview` | Parse and preview Excel requests and output column states |
| `POST` | `/api/batch/upload` | Upload a custom `.xlsx` chemical request workbook |
| `POST` | `/api/batch/select-default` | Reset active batch workbook to `sample_requests_eval.xlsx` |
| `POST` | `/api/batch/start` | Launch asynchronous batch execution via LangGraph and FastMCP |
| `GET` | `/api/batch/status` | Live batch progress, active chemical, stage lifecycle, and row statuses |
| `POST` | `/api/batch/reset` | Clear result columns in Excel for a fresh evaluation run |
| `GET` | `/api/batch/export` | Download updated Excel workbook with confirmed SDS URLs & verdicts |
| `POST` | `/api/sds/search` | Execute single chemical SDS agent verification (secondary entry point) |
| `GET` | `/api/stats` | Aggregated KPI metrics (total, exact matches, review count, avg confidence) |
| `GET` | `/api/history` | Filterable and paginated verification audit records |
| `GET` | `/api/history/{id}` | Deep inspection of a single historical verification |
| `GET` | `/api/review` | Retrieve records flagged for human compliance review |
| `GET` | `/api/trace/latest` | Retrieve the latest LangGraph execution message trace |

---

## 🖥️ Command Center Workspaces

* **Dashboard (`/`)**: Executive overview showing total verifications, resolution rate, subsystem health matrix, verdict distribution chart, and instant CTA to launch batch processing.
* **Batch Processing (`/batch`) — PRIMARY**: Excel upload dropzone, benchmark preset selector, interactive request preview table with real Excel columns, live progress monitor with agent stage telemetry, row inspection modal, and Excel export.
* **Single SDS Search (`/search`)**: Interactive chemical investigation console with pre-populated presets (`Acetone 99%`, `IPA 70%`, `HCl 37%`), live agent timeline, structured decision cards, and document preview modals.
* **Audit History (`/history`)**: Searchable audit log reading directly from `logs/agent_trace.jsonl` with deep LangGraph message trace inspection.
* **Human Review Queue (`/review`)**: Dedicated workspace displaying flagged chemical searches (`NEEDS REVIEW`) requiring expert human validation.
* **Agent Trace Explorer (`/trace`)**: Interactive visual breakdown of the cyclic LangGraph state machine with step-by-step tool invocation payloads.
* **Settings (`/settings`)**: Inference parameters, FastMCP endpoints, masked credentials, and environment diagnostics.

---

## 🧪 Automated Testing

```bash
# Execute pytest test suite:
pytest tests/

# Execute frontend production build:
cd frontend
npm run build
```
