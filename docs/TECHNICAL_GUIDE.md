# L2 SDS Intelligence — Technical Guide & Component Reference

This document serves as the deep-dive technical reference for the **L2 SDS Intelligence** repository. It examines every technology, library, architectural pattern, and protocol that actually exists in this codebase.

For every component, the following seven critical architectural questions are systematically addressed:
1. **What is it?**
2. **Why is it used in this project?**
3. **Where is it used?** (Exact file paths and modules)
4. **How does it work here?** (Implementation specifics and data flows)
5. **What would break if it were removed?**
6. **What alternatives exist?**
7. **Why was the current approach reasonable?**

---

## Table of Contents

1. [Python & Async Runtime](#1-python--async-runtime)
2. [FastAPI Web Framework](#2-fastapi-web-framework)
3. [Pydantic v2 (Data Validation & Schemas)](#3-pydantic-v2-data-validation--schemas)
4. [LangGraph (StateGraph Orchestration)](#4-langgraph-stategraph-orchestration)
5. [LangChain Core & LangChain Groq (LLM Layer)](#5-langchain-core--langchain-groq-llm-layer)
6. [Model Context Protocol (MCP) & FastMCP](#6-model-context-protocol-mcp--fastmcp)
7. [MCP Client (`SDSMCPClient`) & Dynamic Tool Discovery](#7-mcp-client-sdsmcpclient--dynamic-tool-discovery)
8. [MCP Server (`FastMCP("ExcelMCP")`)](#8-mcp-server-fastmcpexcelmcp)
9. [Stdio Transport Subprocess Architecture](#9-stdio-transport-subprocess-architecture)
10. [Web Search Retrieval (`ddgs` / DuckDuckGo)](#10-web-search-retrieval-ddgs--duckduckgo)
11. [PDF Document Parsing (`PyMuPDF` / `fitz`)](#11-pdf-document-parsing-pymupdf--fitz)
12. [HTML Document Parsing (`BeautifulSoup4`)](#12-html-document-parsing-beautifulsoup4)
13. [Excel Processing (`openpyxl` & `pandas`)](#13-excel-processing-openpyxl--pandas)
14. [React 18 & TypeScript Frontend](#14-react-18--typescript-frontend)
15. [Vite 6 Build System & Reverse Proxy](#15-vite-6-build-system--reverse-proxy)
16. [Tailwind CSS Design System](#16-tailwind-css-design-system)
17. [TanStack React Query v5](#17-tanstack-react-query-v5)
18. [Recharts & Lucide React (Visualization & Icons)](#18-recharts--lucide-react-visualization--icons)
19. [API Communication Architecture (Fetch API & Proxy)](#19-api-communication-architecture-fetch-api--proxy)
20. [Environment Configuration (`python-dotenv`)](#20-environment-configuration-python-dotenv)
21. [Structured Telemetry & Audit Logging (`JSONL`)](#21-structured-telemetry--audit-logging-jsonl)
22. [SSRF Network Shield & Security Layer](#22-ssrf-network-shield--security-layer)
23. [DNS Resolution & IP Filtering Engine](#23-dns-resolution--ip-filtering-engine)
24. [Independent Evaluation Benchmark Suite](#24-independent-evaluation-benchmark-suite)
25. [Dependency Management (`requirements.txt` & `package.json`)](#25-dependency-management-requirementstxt--packagejson)

---

## 1. Python & Async Runtime

### 1. What is it?
Python 3.10+ serves as the primary programming language for the backend, agentic workflow, security verification, and evaluation suite. It utilizes Python's built-in `asyncio` event loop for non-blocking I/O.

### 2. Why is it used in this project?
The SDS retrieval pipeline requires high-throughput asynchronous network calls (concurrent search, MCP stdio communication, chunked streaming document fetching) alongside deep document processing (PDF parsing, regular expressions, tabular Excel data manipulation). Python provides the premier ecosystem uniting LangGraph, Pydantic, FastMCP, and PyMuPDF.

### 3. Where is it used?
* Root orchestrators: [`server.py`](file:///C:/Coding/Projects/L2/server.py), [`main.py`](file:///C:/Coding/Projects/L2/main.py), [`evaluate.py`](file:///C:/Coding/Projects/L2/evaluate.py), [`create_test_data.py`](file:///C:/Coding/Projects/L2/create_test_data.py).
* Core application modules: [`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py), [`src/security.py`](file:///C:/Coding/Projects/L2/src/security.py), [`src/sds_parser.py`](file:///C:/Coding/Projects/L2/src/sds_parser.py), [`src/tools.py`](file:///C:/Coding/Projects/L2/src/tools.py), [`src/workbook_utils.py`](file:///C:/Coding/Projects/L2/src/workbook_utils.py), [`src/evaluation.py`](file:///C:/Coding/Projects/L2/src/evaluation.py), [`src/mcp_client.py`](file:///C:/Coding/Projects/L2/src/mcp_client.py), [`src/mcp_server.py`](file:///C:/Coding/Projects/L2/src/mcp_server.py), [`src/schema.py`](file:///C:/Coding/Projects/L2/src/schema.py), [`src/state.py`](file:///C:/Coding/Projects/L2/src/state.py).

### 4. How does it work here?
The application runs on an asynchronous event loop (`asyncio.run()`, `async def`). When batch processing Excel rows or evaluating benchmark datasets, tasks yield control during MCP transport roundtrips and HTTP I/O, preventing thread starvation. Thread-safe locks (`asyncio.Lock()`) protect batch job states in [`server.py: BatchJobManager`](file:///C:/Coding/Projects/L2/server.py#L58-L150).

### 5. What would break if it were removed?
The entire backend, StateGraph execution, MCP server, security filters, and evaluation suite would cease to function.

### 6. What alternatives exist?
Node.js / TypeScript, Go, or Rust.

### 7. Why was the current approach reasonable?
LangGraph, PyMuPDF, and FastMCP have first-class Python support. Python offers unmatched developer velocity for chemical entity parsing (regex, synonyms) and scientific tabular data manipulation.

---

## 2. FastAPI Web Framework

### 2.1 What is it?
FastAPI (`fastapi>=0.110.0`) is a modern, high-performance web framework for building REST APIs with Python based on standard Python type hints and ASGI (`uvicorn`).

### 2.2 Why is it used in this project?
To expose a clean, production-grade REST API connecting the React frontend command center to the LangGraph retrieval agent and MCP batch manager.

### 2.3 Where is it used?
[`server.py`](file:///C:/Coding/Projects/L2/server.py): Defines the ASGI application `app = FastAPI(...)`, CORS middleware, background task runners, and 15 endpoints.

### 2.4 How does it work here?
FastAPI handles incoming HTTP requests asynchronously:
* `GET /api/health`: Reports server, MCP, and batch state.
* `POST /api/sds/search`: Invokes LangGraph for ad-hoc single searches.
* `POST /api/batch/upload`: Accepts multipart Excel file uploads, persists them to `uploads/`, and inspects sheet structures.
* `POST /api/batch/confirm-mapping`: Confirms active request worksheet and column mappings.
* `POST /api/batch/start`: Launches background batch worker processing rows via StateGraph and MCP.
* `GET /api/batch/status`: Streams real-time progress metrics to the UI.
* `GET /api/batch/export`: Downloads the updated workbook with in-place verified columns.
* `GET /api/stats`, `GET /api/history`, `GET /api/review`, `GET /api/trace/latest`: Audit queries reading `logs/agent_trace.jsonl`.

### 2.5 What would break if it were removed?
The React frontend would lose all backend connectivity; users could not trigger single searches, upload workbooks, monitor progress, or export updated spreadsheets via the browser.

### 2.6 What alternatives exist?
Flask, Django REST Framework, or a custom Starlette server.

### 2.7 Why was the current approach reasonable?
FastAPI integrates natively with Pydantic v2, provides out-of-the-box OpenAPI documentation, natively supports `async`/`await` and background tasks, and introduces near-zero serialization overhead.

---

## 3. Pydantic v2 (Data Validation & Schemas)

### 3.1 What is it?
Pydantic (`pydantic>=2.7.0`) is a data validation and settings management library utilizing Python type annotations to enforce strict runtime type safety and serialization.

### 3.2 Why is it used in this project?
LLMs are inherently probabilistic and can generate hallucinated formats, ungrounded URLs, or malformed data structures. Pydantic enforces an impermeable deterministic boundary between LLM output and persistent storage.

### 3.3 Where is it used?
* [`src/schema.py`](file:///C:/Coding/Projects/L2/src/schema.py): Core schemas (`NormalizedSDSRequest`, `SDSEvidence`, `ActionDecision`, `VerificationResult`, `SDSValidationResult`).
* [`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py): LLM structured outputs and verification validation.
* [`server.py`](file:///C:/Coding/Projects/L2/server.py): REST request/response validation models (`SingleSearchRequest`, `MappingConfirmRequest`).

### 3.4 How does it work here?
1. **Dynamic Action Output**: `llm.with_structured_output(ActionDecision)` forces the model to emit valid actions (`SEARCH`, `RANK`, `FETCH`, `VERIFY`, `FINISH`, `RETRY`).
2. **Reflection Validation**: `VerificationResult` validates that field matches (`product_match`, `manufacturer_match`) are boolean, confidence is bounded (`0 <= confidence <= 100`), and reasoning is at least 5 characters.
3. **Strict Grounding Invariant**: In `SDSValidationResult`, a `@model_validator(mode="after")` enforces:
   ```python
   if self.status in ["EXACT MATCH", "BEST AVAILABLE"]:
       if not self.final_url or not str(self.final_url).strip():
           raise ValueError(f"'{self.status}' status requires a valid non-empty grounded final_url.")
   ```
4. **URL Sanitation**: `@field_validator("final_url")` passes all URLs through `is_valid_http_url()`, rejecting malformed or internal hostnames.

### 3.5 What would break if it were removed?
Hallucinated URLs and ungrounded verdicts from the model would leak directly into the database, Excel spreadsheets, and user dashboards without invariant checks.

### 3.6 What alternatives exist?
Marshmallow, Cerberus, jsonschema, or manual procedural dictionary checks.

### 3.7 Why was the current approach reasonable?
Pydantic v2 is implemented in Rust (pydantic-core), making it orders of magnitude faster than Python-based alternatives while serving as the official standard for LangChain structured outputs and FastAPI.

---

## 4. LangGraph (StateGraph Orchestration)

### 4.1 What is it?
LangGraph (`langgraph>=0.0.30`) is a library for building stateful, multi-actor, cyclic agent applications with LLMs using graph-based primitives.

### 4.2 Why is it used in this project?
Safety Data Sheet retrieval cannot be solved with a static linear chain. It requires an agentic state machine capable of dynamic action selection, adaptive retry cycles, conditional routing, and independent verification loops.

### 4.3 Where is it used?
* [`src/state.py`](file:///C:/Coding/Projects/L2/src/state.py): `SDSState` definition.
* [`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py#L1455-L1523): `create_sds_graph()` and node definitions (`decide_action_node`, `search_node`, `rank_node`, `fetch_node`, `draft_decision_node`, `verify_decision_node`, `corrective_action_node`, `extract_final_node`).

### 4.4 How does it work here?
1. Nodes mutate the state dictionary (`SDSState`).
2. Edges connect nodes:
   - `START -> decide_action`
   - `decide_action -> (conditional route_action: search | rank | fetch | decide_action | draft)`
   - `search -> (conditional route_search: rank | decide_action | extract_final)`
   - `rank -> decide_action`
   - `fetch -> (conditional route_fetch: draft | decide_action)`
   - `draft -> verify`
   - `verify -> (conditional route_verification: correct | extract_final)`
   - `correct -> extract_final`
   - `extract_final -> END`
3. A recursion limit of 20 (`{"recursion_limit": 20}`) guarantees graph termination even in abnormal loop conditions.

### 4.5 What would break if it were removed?
The entire multi-step retrieval lifecycle (search -> rank -> fetch -> retry -> verify -> correct) would have to be manually coded as brittle procedural loops with complex state management.

### 4.6 What alternatives exist?
LangChain Legacy AgentExecutor, CrewAI, AutoGen, or custom hardcoded `while` loops.

### 4.7 Why was the current approach reasonable?
LangGraph provides explicit, inspectable state transitions, first-class conditional edges, native async support (`ainvoke`), and full traceability of agent messages and decisions.

---

## 5. LangChain Core & LangChain Groq (LLM Layer)

### 5.1 What is it?
`langchain-core` (`>=0.3.0`) provides base abstractions (messages, tools, prompts). `langchain-groq` (`>=0.1.0`) provides the API client for Groq Cloud's LPU inference engine.

### 5.2 Why is it used in this project?
To power the agent's policy engine (`decide_action_node`) with ultra-fast LLM inference (`openai/gpt-oss-120b`), enabling near-instantaneous decision-making without stalling the batch pipeline.

### 5.3 Where is it used?
[`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py#L47-L61): `get_llm()` initializes `ChatGroq(temperature=0, groq_api_key=..., model_name=...)`.

### 5.4 How does it work here?
* The model is initialized with temperature 0 for deterministic output.
* `decide_action_node` binds Pydantic schemas using `.with_structured_output(ActionDecision)`.
* When an API key is absent or rate limits occur, the system smoothly falls back to deterministic rule-based action selection without crashing.

### 5.5 What would break if it were removed?
Autonomous policy generation would be disabled; the system would operate purely on deterministic fallback rules.

### 5.6 What alternatives exist?
OpenAI API, Anthropic Claude API, local Ollama/vLLM, or pure rule-based heuristics.

### 5.7 Why was the current approach reasonable?
Groq delivers sub-second inference speeds (often >500 tokens/sec), essential for batch-processing hundreds of chemical requests where multi-second API latencies would make bulk processing impractical.

---

## 6. Model Context Protocol (MCP) & FastMCP

### 6.1 What is it?
The **Model Context Protocol (MCP)** is an open industry standard (developed by Anthropic) that defines how AI applications communicate with tools and data sources. **FastMCP** (`mcp<2.0.0`) is a high-level Python framework for building MCP servers and clients.

### 6.2 Why is it used in this project?
1. **Process Isolation**: Untrusted document inspection (downloading external PDFs and running complex parsers) is quarantined in a dedicated subprocess behind the protocol boundary. If an external PDF exploit or memory crash occurs, it does not kill the main web server.
2. **Standardized Tool Interface**: Storage updates (Excel reads and in-place writes) and document inspection are exposed as standardized tools that can be discovered dynamically.

### 6.3 Where is it used?
* Server: [`src/mcp_server.py`](file:///C:/Coding/Projects/L2/src/mcp_server.py) (`FastMCP("ExcelMCP")`).
* Client: [`src/mcp_client.py`](file:///C:/Coding/Projects/L2/src/mcp_client.py) (`SDSMCPClient`).

### 6.4 How does it work here?
The FastMCP server exposes three registered tools:
1. `get_pending_requests`: Reads target rows with automated sheet classification and semantic column mapping.
2. `update_request_status`: Writes verified status, grounded URL, confidence, and reasoning back into Excel in-place.
3. `inspect_sds_document`: Safely downloads and parses candidate documents behind the MCP boundary with SSRF protection.

### 6.5 What would break if it were removed?
Process isolation between untrusted document inspection and agent orchestration would be lost. Excel read/write operations would require direct in-process file locking.

### 6.6 What alternatives exist?
Custom REST microservice, gRPC service, or direct in-process module imports.

### 6.7 Why was the current approach reasonable?
MCP is an emerging open standard designed specifically for AI agent tool integration. Using FastMCP with stdio transport avoids managing additional HTTP network ports, authentication tokens, or external daemon processes.

---

## 7. MCP Client (`SDSMCPClient`) & Dynamic Tool Discovery

### 7.1 What is it?
`SDSMCPClient` ([`src/mcp_client.py`](file:///C:/Coding/Projects/L2/src/mcp_client.py)) is the client-side adapter implementing the standard MCP protocol over stdio.

### 7.2 Why is it used in this project?
To dynamically discover available tools from the connected MCP server, verify their presence, and invoke them safely without hardcoded assumptions.

### 7.3 Where is it used?
[`src/mcp_client.py`](file:///C:/Coding/Projects/L2/src/mcp_client.py), instantiated in [`main.py`](file:///C:/Coding/Projects/L2/main.py#L21), [`server.py`](file:///C:/Coding/Projects/L2/server.py#L22), and [`src/workflow.py: fetch_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L1014-L1054).

### 7.4 How does it work here?
1. **Connection**: `await mcp_client.connect()` launches the MCP server subprocess via `stdio_client` and initializes `ClientSession`.
2. **Dynamic Discovery**: Immediately calls `list_tools()`, sending an MCP protocol query to the server and populating `discovered_tools`:
   ```python
   tools_result = await self._session.list_tools()
   for tool in tools_result.tools:
       self.discovered_tools[tool.name] = {"name": tool.name, "description": ..., "input_schema": ...}
   ```
3. **Verified Invocation**: `call_tool_safe(tool_name, args)` checks `is_tool_available(tool_name)`. If missing, it attempts a force-refresh; if still unavailable, it raises a descriptive `RuntimeError`.

### 7.5 What would break if it were removed?
The LangGraph agent could not discover or execute tools exposed by the MCP server.

### 7.6 What alternatives exist?
Hardcoding tool names and schemas without protocol-level discovery.

### 7.7 Why was the current approach reasonable?
Dynamic protocol discovery satisfies enterprise architectural standards: the client learns tool capabilities and parameter schemas directly from the server at runtime.

---

## 8. MCP Server (`FastMCP("ExcelMCP")`)

### 8.1 What is it?
[`src/mcp_server.py`](file:///C:/Coding/Projects/L2/src/mcp_server.py) is a FastMCP server running as a dedicated service managing tabular data operations and isolated document inspection.

### 8.2 Why is it used in this project?
To act as the single source of truth for reading pending chemical requests from Excel, updating results in-place, and executing sandboxed document fetching.

### 8.3 Where is it used?
[`src/mcp_server.py`](file:///C:/Coding/Projects/L2/src/mcp_server.py), executed as a subprocess by `SDSMCPClient`.

### 8.4 How does it work here?
Decorates Python functions with `@mcp.tool()`:
```python
@mcp.tool()
def get_pending_requests(column_mapping_json: str = "", selected_sheets_json: str = "") -> str: ...

@mcp.tool()
def update_request_status(row_index: int = 0, final_url: str = "", status: str = "", confidence: int = 0, reasoning: str = "", sheet_name: str = "", excel_row: int = 0) -> str: ...

@mcp.tool()
def inspect_sds_document(url: str) -> str: ...
```
When started, `mcp.run()` listens on stdin/stdout, deserializing incoming JSON-RPC calls and serializing responses.

### 8.5 What would break if it were removed?
Excel read/write automation and sandboxed document inspection would fail.

### 8.6 What alternatives exist?
Embedding Excel logic directly into `workflow.py` without boundary isolation.

### 8.7 Why was the current approach reasonable?
Encapsulating storage mutations inside the MCP server creates a clean separation of concerns: the LangGraph agent reasons about compliance, while the MCP server handles physical file I/O.

---

## 9. Stdio Transport Subprocess Architecture

### 9.1 What is it?
The standard input/output (`stdio`) transport mechanism provided by the MCP Python SDK (`mcp.client.stdio.stdio_client`).

### 9.2 Why is it used in this project?
To enable communication between the FastAPI backend/LangGraph agent and the FastMCP server without opening network sockets, avoiding TCP port collisions, firewall blocks, or network configuration overhead.

### 9.3 Where is it used?
[`src/mcp_client.py`](file:///C:/Coding/Projects/L2/src/mcp_client.py#L22-L38).

### 9.4 How does it work here?
1. Client configures `StdioServerParameters(command=sys.executable, args=[".../src/mcp_server.py"], env=env_vars)`.
2. Client spawns server as a child process with redirected pipes.
3. Client reads from server's stdout and writes to server's stdin using framed JSON-RPC messages.
4. On application shutdown, `disconnect()` cleanly closes the pipes and terminates the child process.

### 9.5 What would break if it were removed?
Communication between `SDSMCPClient` and `src/mcp_server.py` would collapse unless replaced with a network socket (SSE/HTTP).

### 9.6 What alternatives exist?
Server-Sent Events (SSE) over HTTP, WebSockets, or Unix domain sockets.

### 9.7 Why was the current approach reasonable?
Stdio transport is zero-config, highly secure (no exposed network ports), operates cross-platform (Windows, Linux, macOS), and life-cycles automatically with the parent process.

---

## 10. Web Search Retrieval (`ddgs` / DuckDuckGo)

### 10.1 What is it?
`ddgs` (`ddgs>=9.0.0`) is the Python library for DuckDuckGo search retrieval.

### 10.2 Why is it used in this project?
To discover publicly accessible Safety Data Sheet documents across official manufacturer portals, chemical databases, and industrial suppliers without requiring costly proprietary search engine API subscriptions.

### 10.3 Where is it used?
[`src/tools.py: search_duckduckgo`](file:///C:/Coding/Projects/L2/src/tools.py#L164-L192), invoked by [`src/workflow.py: search_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L903).

### 10.4 How does it work here?
```python
with DDGS() as ddgs:
    search_res = ddgs.text(query, max_results=max_results)
```
1. Receives validated, sanitized model search queries.
2. Retrieves up to 10 candidates per query.
3. Extracts `url`, `title`, `snippet`, and attaches `source_query`.
4. Filters out invalid URL syntax and deduplicates against already-discovered URLs.
5. Injects 0.3s sleep to avoid rate limiting.

### 10.5 What would break if it were removed?
The system would be unable to discover online SDS candidates for un-cached chemicals.

### 10.6 What alternatives exist?
Google Custom Search API, Bing Search API, Serper, or SerpAPI.

### 10.7 Why was the current approach reasonable?
DuckDuckGo provides effective search yield for industrial chemical queries (`<Company> <Product> SDS filetype:pdf`) without requiring paid API tokens or credit cards, making the project immediately reproducible for evaluators.

---

## 11. PDF Document Parsing (`PyMuPDF` / `fitz`)

### 11.1 What is it?
`PyMuPDF` (`pymupdf>=1.23.0`, imported as `fitz`) is a high-performance Python binding for the MuPDF C library, providing rapid PDF rendering, extraction, and manipulation.

### 11.2 Why is it used in this project?
Over 90% of authentic chemical Safety Data Sheets are published as multi-page PDF documents. PyMuPDF extracts raw text from in-memory byte buffers with unmatched speed and fidelity.

### 11.3 Where is it used?
[`src/sds_parser.py: parse_sds_document`](file:///C:/Coding/Projects/L2/src/sds_parser.py#L228-L240).

### 11.4 How does it work here?
```python
doc = fitz.open(stream=raw_data, filetype="pdf")
pages_to_read = min(len(doc), max_pdf_pages) # Bounded to 10 pages
for page_num in range(pages_to_read):
    text = doc[page_num].get_text()
    if text:
        page_texts.append(text)
full_text = "\n\n".join(page_texts)
```
Operates strictly in memory without writing temporary files to disk.

### 11.5 What would break if it were removed?
Direct PDF SDS parsing would completely fail.

### 11.6 What alternatives exist?
`pypdf`, `pdfplumber`, `pdfminer.six`, or external OCR engines like Tesseract.

### 11.7 Why was the current approach reasonable?
`PyMuPDF` is written in C, making it 10x–20x faster than pure-Python PDF parsers. It cleanly handles complex multi-column SDS layouts and corrupt PDF streams without throwing unhandled crashes.

---

## 12. HTML Document Parsing (`BeautifulSoup4`)

### 12.1 What is it?
`BeautifulSoup4` (`beautifulsoup4>=4.12.0`) is a Python library for parsing structured HTML and XML documents.

### 12.2 Why is it used in this project?
Some chemical suppliers host Safety Data Sheets on interactive web portal pages or landing pages rather than direct static PDF links. BeautifulSoup extracts clean textual content while stripping navigation boilerplate.

### 12.3 Where is it used?
[`src/sds_parser.py: parse_sds_document`](file:///C:/Coding/Projects/L2/src/sds_parser.py#L241-L245).

### 12.4 How does it work here?
```python
soup = BeautifulSoup(raw_data, 'html.parser')
for elem in soup(["script", "style", "nav", "footer"]):
    elem.decompose()
full_text = soup.get_text(separator=' ', strip=True)
```
Strips script, CSS styling, navigation bars, and footers, leaving only pure document body text for GHS section matching.

### 12.5 What would break if it were removed?
HTML-based SDS portal pages could not be extracted or verified.

### 12.6 What alternatives exist?
`lxml`, `html5lib`, or raw regex HTML stripping.

### 12.7 Why was the current approach reasonable?
BeautifulSoup is resilient to malformed, poorly nested HTML commonly encountered on older chemical manufacturer portals.

---

## 13. Excel Processing (`openpyxl` & `pandas`)

### 13.1 What is it?
`pandas` (`>=2.0.0`) is a powerful tabular data analysis library. `openpyxl` (`>=3.1.0`) is a Python library to read and write Excel 2010 xlsx/xlsm/xltx/xltm files.

### 13.2 Why is it used in this project?
Enterprise chemical procurement workflows rely heavily on Excel workbooks containing thousands of chemical line items across multiple departments, squads, or allocation sheets.

### 13.3 Where is it used?
* Ingestion & Analysis: [`src/workbook_utils.py`](file:///C:/Coding/Projects/L2/src/workbook_utils.py) (`inspect_workbook`, `extract_table_from_dataframe`, `classify_sheet`).
* In-Place Update: [`src/mcp_server.py`](file:///C:/Coding/Projects/L2/src/mcp_server.py#L76-L108).
* Test Data Generation: [`create_test_data.py`](file:///C:/Coding/Projects/L2/create_test_data.py).

### 13.4 How does it work here?
1. **Pandas for Inspection**: Rapidly inspects sheet names, header rows, and column values; cleans whitespace and filters null rows.
2. **Openpyxl for In-Place Modification**: Loads workbook without altering existing formulas or unrelated sheets; dynamically appends or updates `Found URL`, `Status`, `Confidence`, and `Reasoning` columns in the exact target row.

### 13.5 What would break if it were removed?
The platform could not ingest client workbooks, map columns, or write verified compliance data back to Excel.

### 13.6 What alternatives exist?
`xlwings`, `xlsxwriter`, or converting workbooks to CSV/SQLite.

### 13.7 Why was the current approach reasonable?
CSV loses multi-sheet structures and formula formatting. `openpyxl` preserves the original Excel formatting while enabling safe, row-level in-place writes.

---

## 14. React 18 & TypeScript Frontend

### 14.1 What is it?
React 18 with TypeScript 5 is the modern frontend UI framework providing declarative, component-based user interfaces with strict compile-time type safety.

### 14.2 Why is it used in this project?
To deliver an executive, interactive dark-theme command center allowing evaluators and compliance officers to monitor real-time batch progress, execute single searches, inspect provenance, and manage review queues.

### 14.3 Where is it used?
[`frontend/src/`](file:///C:/Coding/Projects/L2/frontend/src/): Pages (`DashboardPage`, `SearchPage`, `BatchProcessingPage`, `ReviewPage`, `HistoryPage`, `AgentTracePage`, `SettingsPage`), layout components, and custom hooks.

### 14.4 How does it work here?
* TypeScript interfaces in [`frontend/src/types/sds.ts`](file:///C:/Coding/Projects/L2/frontend/src/types/sds.ts) mirror backend Pydantic models.
* Components use functional React patterns with hooks (`useState`, `useCallback`, `useMemo`, TanStack Query hooks).

### 14.5 What would break if it were removed?
The graphical command center would not exist; all interactions would be confined to terminal CLI scripts.

### 14.6 What alternatives exist?
Vue.js, Svelte, Angular, or backend templates (Jinja2).

### 14.7 Why was the current approach reasonable?
React 18's component ecosystem offers rich interactive libraries (Recharts, Lucide, Tailwind) while TypeScript guarantees that API contracts between frontend and backend remain strictly synchronized.

---

## 15. Vite 6 Build System & Reverse Proxy

### 15.1 What is it?
Vite (`vite>=6.0.1`) is a next-generation frontend development server and build tool that bundles via Rollup and serves source files over native ESM.

### 15.2 Why is it used in this project?
Provides instant dev server startup, hot module replacement (HMR), and an embedded reverse proxy to avoid Cross-Origin Resource Sharing (CORS) complications during development.

### 15.3 Where is it used?
[`frontend/vite.config.ts`](file:///C:/Coding/Projects/L2/frontend/vite.config.ts).

### 15.4 How does it work here?
Runs on port 5173 (`http://127.0.0.1:5173`) and configures a proxy rule forwarding `/api/*` requests to the FastAPI backend on port 8000:
```typescript
server: {
  port: 5173,
  host: '127.0.0.1',
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
}
```

### 15.5 What would break if it were removed?
Frontend asset bundling, TypeScript compilation, and local development proxying would fail.

### 15.6 What alternatives exist?
Webpack, Create React App, Parcel, or Turbopack.

### 15.7 Why was the current approach reasonable?
Vite is the modern industry standard for React apps, offering near-instantaneous HMR compared to legacy Webpack setups.

---

## 16. Tailwind CSS Design System

### 16.1 What is it?
Tailwind CSS (`tailwindcss>=3.4.16`) is a utility-first CSS framework for rapid UI styling.

### 16.2 Why is it used in this project?
To implement a unified, dark-mode enterprise command center aesthetic with ambient glows, glassmorphism, and responsive layouts without writing sprawling custom CSS files.

### 16.3 Where is it used?
[`frontend/tailwind.config.js`](file:///C:/Coding/Projects/L2/frontend/tailwind.config.js), [`frontend/src/index.css`](file:///C:/Coding/Projects/L2/frontend/src/index.css), and across all TSX components.

### 16.4 How does it work here?
Utility classes style status badges, cards, data tables, and modal overlays. Custom theme extensions define glowing neon colors (`emerald-500` for exact matches, `amber-500` for best available, `rose-500` for review flags).

### 16.5 What would break if it were removed?
The application would render unstyled HTML elements.

### 16.6 What alternatives exist?
Bootstrap, Material UI, Chakra UI, or raw CSS modules.

### 16.7 Why was the current approach reasonable?
Tailwind compiles down to a minimal, purged CSS bundle and enables rapid adjustments to typography, spacing, and colors directly in markup.

---

## 17. TanStack React Query v5

### 17.1 What is it?
TanStack React Query (`@tanstack/react-query>=5.62.0`) is an asynchronous state management and server-cache library for React.

### 17.2 Why is it used in this project?
Batch operations, system health, audit logs, and single searches require automatic polling, cache invalidation, deduplication, and loading/error states.

### 17.3 Where is it used?
[`frontend/src/hooks/`](file:///C:/Coding/Projects/L2/frontend/src/hooks/), [`frontend/src/App.tsx`](file:///C:/Coding/Projects/L2/frontend/src/App.tsx).

### 17.4 How does it work here?
* `useQuery({ queryKey: ['batchStatus'], queryFn: api.getBatchStatus, refetchInterval: 1500 })`: Automatically polls batch progress while running.
* Automatically invalidates cached KPI statistics when batch jobs complete.

### 17.5 What would break if it were removed?
The frontend would require manual `useEffect` loops with custom state variables for loading, error, and polling synchronization.

### 17.6 What alternatives exist?
Redux Toolkit, Zustand, SWR, or raw React `useState`/`useEffect`.

### 17.7 Why was the current approach reasonable?
React Query decouples server state from client state, providing robust caching, background polling, and window focus re-fetching out of the box.

---

## 18. Recharts & Lucide React (Visualization & Icons)

### 18.1 What is it?
`recharts` (`>=2.15.0`) is a composable charting library built on React components and SVG. `lucide-react` (`>=0.460.0`) is an open-source icon library.

### 18.2 Why is it used in this project?
To present compliance metrics visually (status breakdown bar charts, confidence distribution pie charts, latency graphs) and provide clean enterprise iconography.

### 18.3 Where is it used?
[`frontend/src/components/dashboard/`](file:///C:/Coding/Projects/L2/frontend/src/components/dashboard/) and layout navigation headers.

### 18.4 How does it work here?
Recharts maps telemetry metrics directly to SVG `<ResponsiveContainer>`, `<BarChart>`, and `<PieChart>` elements with smooth hover tooltips.

### 18.5 What would break if it were removed?
The dashboard would lose all visual charts and UI icons.

### 18.6 What alternatives exist?
Chart.js, D3.js, FontAwesome, or Heroicons.

### 18.7 Why was the current approach reasonable?
Recharts is declarative and React-native, avoiding direct DOM manipulation conflicts common with D3.js or Chart.js wrappers.

---

## 19. API Communication Architecture (Fetch API & Proxy)

### 19.1 What is it?
The browser's native `window.fetch` API wrapped in typed service functions ([`frontend/src/services/api.ts`](file:///C:/Coding/Projects/L2/frontend/src/services/api.ts)).

### 19.2 Why is it used in this project?
To communicate asynchronously with backend REST endpoints using typed promises without bundling heavy HTTP client libraries like Axios.

### 19.3 Where is it used?
[`frontend/src/services/api.ts`](file:///C:/Coding/Projects/L2/frontend/src/services/api.ts).

### 19.4 How does it work here?
Helper function `handleResponse<T>` inspects HTTP status codes. If non-200, it parses JSON error details (`errorJson.detail`) and raises typed errors.

### 19.5 What would break if it were removed?
Frontend could not execute HTTP requests to the backend.

### 19.6 What alternatives exist?
Axios, Superagent, or Ky.

### 19.7 Why was the current approach reasonable?
Modern browsers natively support `fetch`; using native fetch keeps the bundle size lightweight.

---

## 20. Environment Configuration (`python-dotenv`)

### 20.1 What is it?
`python-dotenv` (`>=1.0.0`) reads key-value pairs from a `.env` file and sets them as OS environment variables.

### 20.2 Why is it used in this project?
To decouple secret API keys (`GROQ_API_KEY`), model configurations, and file paths from source code, preventing credential leakage in git repositories.

### 20.3 Where is it used?
[`server.py`](file:///C:/Coding/Projects/L2/server.py#L19), [`main.py`](file:///C:/Coding/Projects/L2/main.py#L13), [`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py).

### 20.4 How does it work here?
`dotenv.load_dotenv()` runs at module import, populating `os.environ`. Key variables:
* `GROQ_API_KEY`: API token for Groq Cloud.
* `GROQ_MODEL`: Model identifier (`openai/gpt-oss-120b`).
* `EXCEL_FILE_PATH`: Target benchmark spreadsheet.
* `HOST` & `PORT`: Server binding options.

### 20.5 What would break if it were removed?
API keys and settings would need to be passed as command-line flags or hardcoded in source files.

### 20.6 What alternatives exist?
System environment variables or HashiCorp Vault.

### 20.7 Why was the current approach reasonable?
Standard 12-factor application methodology; developers and evaluators can easily test with a local `.env` file copied from `.env.example`.

---

## 21. Structured Telemetry & Audit Logging (`JSONL`)

### 21.1 What is it?
JSON Lines (`.jsonl`) is a structured format where each line is a valid, independent JSON object.

### 21.2 Why is it used in this project?
Compliance officers and evaluators must be able to audit every decision made by the AI agent: what search query was executed, what candidates were discovered, what scores were computed, what document text was parsed, and why a specific status was determined.

### 21.3 Where is it used?
* Trace file: [`logs/agent_trace.jsonl`](file:///C:/Coding/Projects/L2/logs/agent_trace.jsonl).
* Benchmark logs: [`logs/evaluation_runs/`](file:///C:/Coding/Projects/L2/logs/evaluation_runs/).

### 21.4 How does it work here?
After each chemical request completes (in `main.py` or `server.py`), a structured dictionary is appended to `logs/agent_trace.jsonl`:
```python
trace_entry = {
    "id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "sheet_name": sheet_name,
    "excel_row": excel_row,
    "request": req,
    "final_status": status,
    "final_url": url,
    "confidence": confidence,
    "detailed_reasoning": reasoning,
    "verification_result": ...,
    "provenance": ...,
    "messages": ...
}
```
Endpoints in `server.py` read this file backwards to power the Audit History and Review Queue pages.

### 21.5 What would break if it were removed?
Traceability, UI audit history, review queue classification, and offline debugging would be completely disabled.

### 21.6 What alternatives exist?
Relational database (PostgreSQL/SQLite), document database (MongoDB), or unstructured log text.

### 21.7 Why was the current approach reasonable?
JSONL is append-only, human-readable, requires zero external database installation, and streams easily with simple line-by-line reads.

---

## 22. SSRF Network Shield & Security Layer

### 22.1 What is it?
A custom, multi-tier Server-Side Request Forgery (SSRF) defense shield implemented in [`src/security.py`](file:///C:/Coding/Projects/L2/src/security.py).

### 22.2 Why is it used in this project?
The agent automatically fetches candidate URLs discovered on the public web. Without SSRF defenses, an attacker could supply inputs that cause the server to query internal networks, AWS/GCP cloud metadata endpoints (`169.254.169.254`), or localhost management services.

### 22.3 Where is it used?
[`src/security.py`](file:///C:/Coding/Projects/L2/src/security.py): `validate_url_safety()`, `SafeRedirectHandler`, `safe_fetch_document()`.

### 22.4 How does it work here?
1. **Pre-flight URL Syntax Check**: Only `http` and `https` schemes permitted; URL length bounded (8–2048 chars).
2. **Blocked Domain Checks**: Direct rejection of `localhost`, `127.0.0.1`, `metadata.google.internal`, `instance-data`, and internal suffixes (`.local`, `.internal`, `.lan`, `.corp`, etc.).
3. **Pre-flight DNS & IP Validation**: Resolves hostname to all IP addresses via `socket.getaddrinfo` and checks every resolved IP against `BLOCKED_IP_NETWORKS`.
4. **Per-Hop Redirect Validation**: Custom `SafeRedirectHandler(urllib.request.HTTPRedirectHandler)` validates every redirect hop (max 5 hops) to prevent redirect-based SSRF pivoting.
5. **Bounded Streaming**: Enforces 64 KB chunked reads with a strict 10 MB document limit to prevent memory exhaustion attacks.

### 22.5 What would break if it were removed?
The application would be vulnerable to critical SSRF exploits, intranet scanning, cloud credential theft, and memory denial-of-service attacks.

### 22.6 What alternatives exist?
OS-level network sandboxing, dedicated egress proxy, or containerized network isolation.

### 22.7 Why was the current approach reasonable?
Application-level defense-in-depth requires zero special infrastructure, works identically across local dev and production, and catches attacks before any socket data connection is established.

---

## 23. DNS Resolution & IP Filtering Engine

### 23.1 What is it?
Low-level network address inspection combining Python's standard `socket` and `ipaddress` modules.

### 23.2 Why is it used in this project?
Hostnames can be crafted to disguise private IP addresses (e.g., decimal IP notation, custom DNS servers pointing `safe.evil.com` to `127.0.0.1`). Inspecting resolved IP addresses is the only reliable way to prevent IP obfuscation bypasses.

### 23.3 Where is it used?
[`src/security.py: is_ip_blocked & validate_url_safety`](file:///C:/Coding/Projects/L2/src/security.py#L48-L156).

### 23.4 How does it work here?
Maintains `BLOCKED_IP_NETWORKS`:
* `127.0.0.0/8` (IPv4 loopback)
* `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 private)
* `169.254.0.0/16` (Link-Local / AWS/GCP/Azure Cloud Metadata)
* `100.64.0.0/10` (Carrier-grade NAT)
* `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` (TEST-NET)
* `::1/128` (IPv6 loopback)
* `fc00::/7` (IPv6 Unique Local Address)
* `fe80::/10` (IPv6 Link-Local)

Every resolved IP is parsed into `ipaddress.ip_address` and evaluated against these subnets.

### 23.5 What would break if it were removed?
Attackers could bypass domain filters using DNS rebinding, internal IP literals, or zero-IP notation.

### 23.6 What alternatives exist?
Hardcoded string checks for "127.0.0.1" (vulnerable to decimal, hex, and alternative subnet encodings).

### 23.7 Why was the current approach reasonable?
`ipaddress.ip_network` performs strict binary subnet matching, completely immune to string-formatting tricks.

---

## 24. Independent Evaluation Benchmark Suite

### 24.1 What is it?
A benchmark suite in [`src/evaluation.py`](file:///C:/Coding/Projects/L2/src/evaluation.py), executed via [`evaluate.py`](file:///C:/Coding/Projects/L2/evaluate.py) against [`data/ground_truth.json`](file:///C:/Coding/Projects/L2/data/ground_truth.json).

### 24.2 Why is it used in this project?
To measure the true accuracy, grounding fidelity, and abstention capabilities of the system using an independent ground truth dataset without circular self-scoring.

### 24.3 Where is it used?
[`evaluate.py`](file:///C:/Coding/Projects/L2/evaluate.py), [`src/evaluation.py`](file:///C:/Coding/Projects/L2/src/evaluation.py), [`data/ground_truth.json`](file:///C:/Coding/Projects/L2/data/ground_truth.json).

### 24.4 How does it work here?
1. Loads 15 multi-class benchmark cases:
   - Positive cases: `EXACT MATCH`, `BEST AVAILABLE`
   - Negative cases: missing product identity, non-existent chemicals, manufacturer discrepancies, exhausted searches, SSRF attack parameters.
2. Runs each case through `create_sds_graph()`.
3. **Non-Circular Verification**:
   - Compares predicted status against expected status strictly.
   - Evaluates URL grounding: checks if URL netloc matches `acceptable_domains` or `acceptable_urls`.
   - Evaluates abstention: negative cases must return `NEEDS REVIEW` with an empty URL to pass.
4. Generates a comprehensive markdown report ([`evaluation_report.md`](file:///C:/Coding/Projects/L2/evaluation_report.md)) and JSON telemetry file in `logs/evaluation_runs/`.

### 24.5 What would break if it were removed?
The team and evaluators could not independently assess retrieval accuracy or measure regression impacts.

### 24.6 What alternatives exist?
Ad-hoc manual checking or trusting the model's internal confidence scores.

### 24.7 Why was the current approach reasonable?
Separating the evaluator from the application logic ensures objective scoring. Ground truth rules enforce real domain matching rather than fuzzy string overlap.

---

## 25. Dependency Management (`requirements.txt` & `package.json`)

### 25.1 What is it?
Manifest files defining exact package dependencies:
* Backend: [`requirements.txt`](file:///C:/Coding/Projects/L2/requirements.txt) & [`requirements-lock.txt`](file:///C:/Coding/Projects/L2/requirements-lock.txt).
* Frontend: [`frontend/package.json`](file:///C:/Coding/Projects/L2/frontend/package.json) & [`frontend/package-lock.json`](file:///C:/Coding/Projects/L2/frontend/package-lock.json).

### 25.2 Why is it used in this project?
To guarantee reproducible environment setup across different developer workstations, CI pipelines, and evaluator machines.

### 25.3 Where is it used?
Root workspace and `frontend/` directory.

### 25.4 How does it work here?
* `pip install -r requirements.txt` installs Python packages pinned to compatible versions.
* `npm install` installs frontend packages with exact sub-dependency trees locked via `package-lock.json`.
* Both lockfiles have been curated to eliminate unused libraries (e.g. legacy `chromadb` entries).

### 25.5 What would break if it were removed?
Environment setup would produce mismatched library versions, leading to runtime incompatibilities.

### 25.6 What alternatives exist?
Poetry, Pipenv, Conda, or Docker container images.

### 25.7 Why was the current approach reasonable?
Standard `pip` and `npm` require zero specialized tooling, ensuring immediate compatibility across standard development environments.
