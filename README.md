# L2 SDS Intelligence

<div align="center">

**Agentic Intelligence Platform for Safety Data Sheet Discovery, Verification & Compliance Batch Processing**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.3-cyan.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Dynamic%20ReAct-purple.svg)](https://www.langchain.com/langgraph)
[![FastMCP](https://img.shields.io/badge/MCP-Standard%20Protocol-green.svg)](https://github.com/jlowin/fastmcp)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-Command%20Center%20Dark-38bdf8.svg)](https://tailwindcss.com/)

</div>

---

## 🌟 Overview

Chemical Safety Data Sheets (SDS) are distributed across fragmented manufacturer portals, regulatory repositories, and distributor databases. Locating, verifying, and validating the exact SDS for a specific product, manufacturer, jurisdiction, and language is a critical, high-friction compliance task.

**L2 SDS Intelligence** is an advanced agentic AI platform for chemical Safety Data Sheet retrieval and multi-stage verification. It pairs dynamic **LangGraph action selection** with **independent reflection & programmatic verification**, **SSRF-safe streaming document fetching**, **strict Pydantic schemas**, and a **FastMCP Excel storage transport boundary**:

```text
User / Batch Request (Excel / API)
        ↓
FastMCP Server reads pending request rows
        ↓
Extracts Product / Manufacturer / Country / Language / Part Number / CAS
        ↓
Dynamic Action Selection (SEARCH / RANK / FETCH / DRAFT / VERIFY / RETRY / FINISH)
        ↓
Targeted Discovery & Heuristic Ranking (0–100 utility score)
        ↓
SSRF-Safe Document Fetching & Multi-Page PDF Section Parser
        ↓
Independent Reflection & Verification Stage (Field matching, Grounding check, Downgrading)
        ↓
Strict Pydantic Validation (SDSValidationResult)
        ↓
FastMCP writes Found URL, Status, Confidence, Reasoning back to Excel
        ↓
Interactive Web Command Center & Human Review Queue
```

> **Retrieval Before Generation**: Compliance verdicts are derived strictly from raw text extracted from real manufacturer PDF documents rather than generative synthesis. Zero hallucinated URLs are permitted.

---

## 🚀 Key Architectural Capabilities

* **Dynamic Action Selection**: The agent evaluates state, prerequisites, and observations to choose discrete actions (`SEARCH`, `RANK`, `FETCH`, `VERIFY`, `RETRY`, `FINISH`) across multiple execution paths.
* **Independent Reflection & Verification Stage**: A dedicated verification stage that independently cross-checks draft decisions against extracted document evidence, manufacturer identity, product names, part numbers, and grounding invariants.
* **Strict Grounding Invariant**: Every positive verdict must be grounded: the final URL must have been discovered in search and successfully fetched. Hallucinated or placeholder URLs are rejected and downgraded.
* **Comprehensive SSRF & Network Security**: Streamed chunked downloads with 10MB bounds, DNS resolution checks, loopback/private/link-local/metadata IP filtering, and per-hop redirect re-validation.
* **Multi-Page SDS Extraction**: Deep PDF parsing of key GHS/OSHA sections, CAS numbers, catalog identifiers, revision dates, and language indicators.
* **Strict Pydantic Validation**: Strict runtime validation of status literals (`EXACT MATCH`, `BEST AVAILABLE`, `NEEDS REVIEW`), bounded confidence (`0 <= confidence <= 100`), and valid HTTP/HTTPS URLs.
* **FastMCP Persistent Storage**: Standardized Model Context Protocol (MCP) server managing Excel reads and in-place updates over `stdio` transport.
* **Isolated Batch Jobs**: Thread-safe, request-scoped job management avoiding unsafe global state mutations.
* **Reproducible Evaluation Benchmark**: Ground-truth dataset (`data/ground_truth.json`) with versioned run tracking, field-level accuracy, and automated report generation (`evaluation_report.md`).

---

## 🏛️ Architecture Specification

For detailed architectural schematics, state transitions, security defenses, and component breakdown, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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
│              LangGraph StateGraph Engine               │
│   (Action Decision -> Search -> Rank -> Safe Fetch)    │
│                           │                            │
│                           ▼                            │
│         [ Independent Verification Node ]              │
│       (Grounding Check & Evidence Consistency)         │
│                           │                            │
│                           ▼                            │
│         [ Strict Pydantic Output Extraction ]          │
└───────────────────────────┬────────────────────────────┘
                            │ Stdio Transport
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastMCP Protocol Server                  │
│             (Excel Storage & Audit Logs)               │
└────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing & Verification

Run the full backend test suite:
```bash
python -m pytest -v -p no:cacheprovider tests
```

Run test suite categories independently:
```bash
# Unit & Integration Tests
python -m pytest -v -p no:cacheprovider tests --ignore=tests/test_mcp_client.py

# Isolated FastMCP Stdio Roundtrip Test
python -m pytest -v -p no:cacheprovider tests/test_mcp_client.py
```

Run compilation check:
```bash
python -m compileall -q src main.py server.py evaluate.py
```

Build the frontend:
```bash
cd frontend && npm run build
```

Run reproducible evaluation benchmark:
```bash
python evaluate.py
```

---

## 📦 Setup & Execution

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` and set optional LLM keys:
   ```bash
   GROQ_API_KEY=your_api_key_here
   GROQ_MODEL=openai/gpt-oss-120b
   ```

3. **Start the API Server**:
   ```bash
   python server.py
   ```

4. **Start the Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
