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
│   │ (LLM + Guards)   │      │(Model Query)│      └──────┬───────┘              │
│   └────────┬─────────┘      └─────────────┘             │                      │
│            ▲                                            │                      │
│            │           ┌────────────────────────────────┘                      │
│            │           ▼                                                       │
│            │    ┌──────────────┐      ┌─────────────────┐                      │
│            └─── │  fetch_node  │ ───► │  draft_decision │                      │
│                 │ (MCP Inspect)│      └────────┬────────┘                      │
│                 └──────────────┘               │                               │
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
│                                                                       │        │
└───────────────────────────────────────────────────────────────────────┼────────┘
                                                                        │ Verified Result
                                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FastMCP Protocol Transport Boundary                     │
│              - MCP Tool Discovery (list_tools)                                  │
│              - Excel Reading / Pending Requests (get_pending_requests)          │
│              - In-Place Result Updates (update_request_status)                  │
│              - Safe Document Inspection (inspect_sds_document)                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Architectural Components

### 3.1 Dynamic Action Selection & Agentic Search (`src/workflow.py`)
* **LLM Policy Engine**: Analyzes request context, candidate history, fetched evidence, and previous queries to generate structured `ActionDecision`.
* **Agentic Search Query Execution**: When the LLM chooses `SEARCH` or `RETRY`, its validated model-selected `search_query` is the exact query executed by the search mechanism.
* **Adaptive Retry**: The LLM receives prior search queries and failed attempts to formulate distinct, adaptive queries (e.g. CAS numbers, part numbers, or relaxed company tokens) rather than repeating identical searches.
* **Deterministic Action Prerequisite Guards**:
  - `SEARCH`: Prerequisite: valid chemical product identity + search budget.
  - `RANK`: Prerequisite: discovered candidates non-empty.
  - `FETCH`: Prerequisite: unvisited candidate in discovered set.
  - `RETRY`: Prerequisite: prior attempt exists + retry budget (`retry_count < 2`).
  - `FINISH`: Prerequisite: valid terminal condition (evidence gathered or attempts exhausted).

### 3.2 Independent Reflection & Verification Stage
* Programmatically cross-checks draft decisions against ground truth request parameters, discovered URLs, and raw fetched document payloads:
  - **Strict Grounding Invariant**: Both `EXACT MATCH` and `BEST AVAILABLE` strictly require non-empty grounded URLs.
  - **Authenticity Check**: Verifies presence of standard GHS/OSHA SDS sections.
  - **Manufacturer Match**: Cross-checks company names; downgrades `EXACT MATCH` -> `BEST AVAILABLE` or `NEEDS REVIEW` on discrepancy.
  - **Product Match**: Verifies chemical identity tokens against document text.
  - **Confidence Calibration**: Strict bounded confidence (`0 <= confidence <= 100`).

### 3.3 FastMCP Tool Discovery & Protocol Boundary (`src/mcp_client.py` & `src/mcp_server.py`)
* Standard Model Context Protocol (MCP) server over `stdio` transport.
* **Dynamic Tool Discovery**: `SDSMCPClient` queries the server using `list_tools()` upon connection. Discovered tool definitions are verified dynamically before invocation.
* **Tools Registered**:
  - `get_pending_requests`: Reads target rows with automated sheet classification and semantic column mapping.
  - `update_request_status`: Writes verified status, grounded URL, confidence, and reasoning back into Excel in-place.
  - `inspect_sds_document`: Safely downloads and parses candidate documents behind the MCP boundary with SSRF protection.

### 3.4 Multi-Dataset Workbook Ingestion (`src/workbook_utils.py`)
* Dynamically detects multiple genuine SDS request datasets (e.g., Part1, Part2, Part3) and separates them from summary / operational tables.
* Excludes unrelated data without hardcoded sheet names.
* Presents detected datasets to the user; user selects ONE request set to become active, preserving row-level alignment.

### 3.5 SSRF & Network Safety Layer (`src/security.py`)
* **Scheme Restriction**: Strictly `http` and `https` allowed; blocks `file://`, `ftp://`, `gopher://`.
* **IP Filtering**: DNS resolution verifies that resolved IP addresses do not belong to loopback (`127.0.0.0/8`, `::1`), private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), or cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
* **Redirect Safety**: Intercepts redirect hops and re-validates each target URL against SSRF policy before connection.
* **Stream Bounds**: Reads downloads in 64KB chunks up to a strict 10MB maximum limit.

### 3.6 Multi-Class Benchmark Evaluation (`data/ground_truth.json` & `src/evaluation.py`)
* Evaluates positive, negative, and ambiguous test cases spanning:
  1. `EXACT MATCH`
  2. `BEST AVAILABLE`
  3. `NEEDS REVIEW`
  4. `WRONG PRODUCT`
  5. `WRONG MANUFACTURER`
  6. `WRONG COUNTRY/JURISDICTION`
  7. `WRONG LANGUAGE`
  8. `NO SDS / NO VALID DOCUMENT`
  9. `AMBIGUOUS CASE`
  10. `SECURITY REJECTION`
* Calculates non-circular metrics: status classification accuracy, URL grounding integrity, negative case handling rate, and field-level accuracy.
