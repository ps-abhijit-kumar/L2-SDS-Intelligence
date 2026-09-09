# L2 SDS Intelligence — End-to-End System Flow Reference

This document details the complete runtime flow of the **L2 SDS Intelligence** platform from initial request receipt to final verified output, audit logging, and spreadsheet update.

Every stage outlines its exact **Input**, **Processing**, **Output**, **Responsible Module/File**, **Core Data Structures**, and **Transition to the Next Stage**.

---

## 1. High-Level Runtime Flowchart

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      STAGE 0: REQUEST INGESTION & DISCOVERY                       │
│  Option A: Single Search UI (POST /api/sds/search)                               │
│  Option B: Batch Excel Upload (POST /api/batch/upload -> POST /api/batch/start)  │
│  Option C: CLI Batch Execution (python main.py via FastMCP stdio)                │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Initial State Seed
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│             STAGE 1: STATEGRAPH INITIALIZATION (src/state.py, SDSState)           │
│  Initializes messages, candidate pools, fetch caches, retry counters, provenance │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Invokes StateGraph
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│       STAGE 2: DYNAMIC ACTION SELECTION NODE (src/workflow.py: decide_action)    │
│  1. Check fast-path abstention (empty product, SSRF vectors in parameters)       │
│  2. Enforce hard iteration (<=6) & fetch (<=3) budgets                           │
│  3. Consult Groq LLM (openai/gpt-oss-120b) for structured ActionDecision         │
│  4. Deterministic Prerequisite Guards validate & repair action choice            │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Action Decision
        ┌────────────────────────────────┼────────────────────────────────┐
        │ SEARCH                         │ RANK                           │ FETCH
        ▼                                ▼                                ▼
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│   STAGE 3: SEARCH      │      │   STAGE 4: RANKING     │      │   STAGE 5: FETCHING    │
│  (src/workflow.py:     │      │  (src/workflow.py:     │      │  (src/workflow.py:     │
│   search_node)         │      │   rank_node)           │      │   fetch_node)          │
│                        │      │                        │      │                        │
│ • Validates model query│      │ • Stage A Metadata     │      │ • Routes through MCP   │
│ • Calls DDGS search    │      │   Scoring (0-100)      │      │   inspect_sds_document │
│ • Queries auth domain  │ ───► │ • Chemical synonyms    │ ───► │ • SSRF Network Shield  │
│ • Appends candidates   │      │ • Aggregator demotion  │      │ • Stream chunked (10MB)│
│ • Dedupes URLs         │      │ • Sorts candidate pool │      │ • Parses PDF / HTML    │
└───────────┬────────────┘      └───────────┬────────────┘      └───────────┬────────────┘
            │                               │                               │
            └───────────────────────────────┼───────────────────────────────┘
                                            │ Unvisited URLs / Retry Loops
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│         STAGE 6: DRAFT DECISION NODE (src/workflow.py: draft_decision_node)       │
│  1. Executes Stage B Document-First Evidence Scoring (score_document_evidence)   │
│  2. Evaluates GHS section presence, chemical synonyms, manufacturer tokens       │
│  3. Formulates initial draft status, confidence, and candidate URL               │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Draft Decision
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│    STAGE 7: INDEPENDENT VERIFICATION NODE (src/workflow.py: verify_decision)     │
│  1. SSRF Input Parameter Check                                                   │
│  2. Provenance Grounding Check: URL must be in discovered_urls & successful_fetch│
│  3. Independent Document Evidence Verification (Section 1, Section 3, Section 15)│
│  4. Enforces Grounding Invariants: EXACT MATCH & BEST AVAILABLE require non-empty │
│     grounded URL; NEEDS REVIEW requires empty URL.                                │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Approved or Discrepancies
                   ┌─────────────────────┴─────────────────────┐
                   │ Discrepancies Detected                    │ Approved
                   ▼                                           ▼
┌───────────────────────────────────────┐   ┌──────────────────────────────────────┐
│   STAGE 8: CORRECTIVE ACTION NODE     │   │                                      │
│  (src/workflow.py: corrective_action) │   │                                      │
│ • Adjusts status (downgrades to       │   │                                      │
│   BEST AVAILABLE or NEEDS REVIEW)     │──►│   STAGE 9: EXTRACT FINAL NODE        │
│ • Clears URL if ungrounded            │   │  (src/workflow.py: extract_final)    │
│ • Calibrates bounded confidence score │   │ • Binds provenance metadata          │
└───────────────────────────────────────┘   │ • Classifies review category         │
                                            │ • Validates via SDSValidationResult  │
                                            └──────────────────┬───────────────────┘
                                                               │ Final Result
                                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│               STAGE 10: WRITEBACK, AUDIT TRACING & USER PRESENTATION             │
│  1. FastMCP update_request_status writes in-place to target Excel worksheet      │
│  2. server.py appends structured JSONL entry to logs/agent_trace.jsonl           │
│  3. React Frontend updates KPI cards, search report, audit history, review queue │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Runtime Stages

### Stage 0: Request Ingestion & Data Preparation

#### Path A: Single Ad-Hoc Interactive Search
* **Input**: User fills search form in UI (`product_name`, `manufacturer`, `country`, `language`, optional `part_number`, `cas_number`).
* **Processing**:
  1. Frontend submits JSON payload to `POST /api/sds/search`.
  2. FastAPI parses payload into `SDSSearchRequest` Pydantic model (`server.py`).
  3. Prepares row dictionary: `{"Product Name": ..., "Company": ..., "Country": ..., "Language": ..., "Part Number": ..., "CAS": ...}`.
* **Output**: Request dictionary ready for state graph invocation.
* **Responsible File**: [`server.py`](file:///C:/Coding/Projects/L2/server.py#L650-L725), [`frontend/src/pages/SearchPage.tsx`](file:///C:/Coding/Projects/L2/frontend/src/pages/SearchPage.tsx).
* **Next Stage**: Stage 1 (Seed State Construction).

#### Path B: Batch Multi-Sheet Excel Ingestion
* **Input**: An Excel workbook (`.xlsx`) uploaded via `POST /api/batch/upload` or default file (`sample_requests_eval.xlsx`).
* **Processing**:
  1. `inspect_workbook` in [`src/workbook_utils.py`](file:///C:/Coding/Projects/L2/src/workbook_utils.py#L199-L350) scans all sheets in the workbook.
  2. Detects header rows within the first 8 rows via `extract_table_from_dataframe`.
  3. Maps column headers semantically to standard fields (`product`, `company`, `part_number`, `country`, `language`, `status`, `found_url`, `confidence`, `reasoning`) using `COLUMN_SYNONYMS`.
  4. Classifies each worksheet into `SDS_REQUESTS`, `SUPPORTING_DATA`, `SUMMARY`, or `UNKNOWN` using `classify_sheet`.
  5. User selects the single active request sheet via `POST /api/batch/confirm-mapping`.
  6. `BatchJobManager` in `server.py` locks batch execution, initializes thread-safe state, and processes rows sequentially.
* **Output**: Normalized queue of request rows (`List[Dict[str, Any]]`) with `_sheet_name`, `_excel_row`, and `_row_index` markers.
* **Responsible File**: [`src/workbook_utils.py`](file:///C:/Coding/Projects/L2/src/workbook_utils.py), [`server.py`](file:///C:/Coding/Projects/L2/server.py#L55-L160).
* **Next Stage**: Stage 1 (Sequential Row Execution).

---

### Stage 1: StateGraph Initialization & Seed State Construction

* **Input**: Single chemical request dictionary (`row_data`) and optional connected `SDSMCPClient`.
* **Processing**:
  1. Builds `SDSState` dictionary conforming to [`src/state.py`](file:///C:/Coding/Projects/L2/src/state.py).
  2. Seeds empty collections for `discovered_candidates`, `ranked_candidates`, `fetched_urls`, `successful_fetches`, `failed_fetches`, `search_queries`, `action_history`.
  3. Seeds execution bounds: `iteration_count = 0`, `retry_count = 0`, `current_search_query = None`, `current_candidate_url = ""`.
  4. Passes `mcp_client` reference so downstream nodes can invoke MCP tools.
* **Output**: Initial `SDSState` object passed to `graph.ainvoke(initial_state, config={"recursion_limit": 20})`.
* **Responsible File**: [`src/state.py`](file:///C:/Coding/Projects/L2/src/state.py), [`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py#L1455-L1523).
* **Data Structure**: `SDSState` (TypedDict with LangGraph message channels).
* **Next Stage**: Stage 2 (`decide_action_node`).

---

### Stage 2: Dynamic Action Selection & Prerequisite Verification

* **Input**: Current `SDSState` containing request parameters, discovered candidates, fetch history, action history, and iteration counters.
* **Processing**:
  1. **Fast-Path Rejections**:
     - If `Product Name` is missing/empty, or if any input parameter contains SSRF patterns (`127.0.0.1`, `localhost`), immediately select `FINISH` with `policy_source = "fallback"`.
  2. **Budget Enforcement**:
     - If `len(fetched_urls) >= 3`: Select `FINISH` (candidate fetch budget exhausted).
     - If `iteration_count > 6` or `retry_count >= 2`: Select `FINISH` (hard iteration budget reached).
  3. **LLM Policy Consultation** (if `GROQ_API_KEY` configured):
     - Formats prompt with request identity, executed queries, untrusted candidate summaries, fetched URLs, and discovered MCP tools.
     - Calls `llm.with_structured_output(ActionDecision)` via ChatGroq (`openai/gpt-oss-120b`).
     - Tracks model latency (`policy_latency_ms`) and logs errors if LLM fails.
  4. **Deterministic Prerequisite Guards**:
     - `SEARCH`: Prerequisite: valid chemical identity + query budget.
     - `RANK`: Prerequisite: candidate pool has unranked URLs. If none, redirects to `SEARCH` or `FINISH`.
     - `FETCH`: Prerequisite: unvisited candidate URL exists in candidate pool. If none, redirects to `RETRY` or `FINISH`.
     - `RETRY`: Prerequisite: prior queries exist + `retry_count < 2`. Automatically calls `generate_adaptive_query` to generate a non-identical query (incorporating CAS, catalog ID, or relaxed terms).
     - `FINISH`: Valid terminal state.
* **Output**: Updated state dictionary with `next_action`, `current_candidate_url`, `current_search_query`, updated `retry_count`, and appended `action_history` entry.
* **Responsible File**: [`src/workflow.py: decide_action_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L555-L856).
* **Data Structure**: `ActionDecision` Pydantic model (`action`, `reason`, `target_url`, `search_query`, `retry_count`).
* **Routing Decision** (`route_action`):
  - `"SEARCH"` -> `search_node`
  - `"RANK"` -> `rank_node`
  - `"FETCH"` -> `fetch_node`
  - `"RETRY"` -> `decide_action_node`
  - `"FINISH"` -> `draft_decision_node`

---

### Stage 3: Agentic Search Execution (`search_node`)

* **Input**: State with `current_search_query` (model-selected or generated) and `row_data`.
* **Processing**:
  1. Validates and sanitizes search query via `validate_search_query`: bounds length (3–300 chars), strips control characters, rejects embedded SSRF IPs/URLs.
  2. Executes targeted web search via `search_duckduckgo(query, max_results=10)`.
  3. Deduplicates URLs against already discovered candidates via `normalize_url`.
  4. Detects manufacturer official domains via `get_authorized_domains_for_manufacturer`. If official domain candidates were not surfaced in the primary query, executes an auxiliary query (`site:<authorized_domain> <product> SDS`).
  5. Appends all unique candidates to `discovered_candidates` with discovery timestamp, snippet, title, domain, and `is_pdf` flag.
* **Output**: `discovered_candidates` list enriched; query appended to `search_queries`.
* **Responsible File**: [`src/workflow.py: search_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L858-L970), [`src/tools.py: search_duckduckgo`](file:///C:/Coding/Projects/L2/src/tools.py#L164-L192).
* **Routing Decision** (`route_search`):
  - If candidates discovered: routes to `rank_node`.
  - If no candidates discovered: routes back to `decide_action_node`.
  - If already marked NEEDS REVIEW (missing parameters): routes to `extract_final_node`.

---

### Stage 4: Search Result Candidate Ranking (`rank_node`)

* **Input**: `discovered_candidates` list and target request criteria.
* **Processing**:
  1. Invokes `rank_sds_candidates` ([`src/tools.py`](file:///C:/Coding/Projects/L2/src/tools.py#L194-L372)) to compute Stage A heuristic scores (0–100):
     - **Product Match Score (0–30)**: Exact name containment, chemical synonyms (`CHEMICAL_SYNONYMS`), or chemical noun token overlap.
     - **Manufacturer Match Score (0–40)**: Official domain match (+40), trusted distributor (+15), snippet match (+5–10), competing manufacturer domain demotion.
     - **Part / CAS Match Score (0–15)**: Presence of requested CAS or part number in URL, title, or snippet.
     - **Document Type Score (0–15)**: Direct PDF URL (+15) vs. SDS portal URL (+10) vs. generic HTML (+6).
     - **Country / Jurisdiction Score (0–5)**: Jurisdiction keywords (e.g. OSHA, ANSI for US; WHMIS for Canada; REACH for EU).
     - **Language Score (0–5)**: Target language indicators.
     - **Trusted Domain Bonus (0–10)**: Known chemical distributors (Sigma-Aldrich, Fisher, VWR, etc.).
     - **Aggregator Demotion Penalty (-35)**: Heavy penalty for scraper/aggregator sites (ChemicalBook, GuideChem, ChemBlink, etc.).
  2. Sorts candidates in descending order of score.
  3. Identifies top unvisited candidate URL as `current_candidate_url`.
* **Output**: `ranked_candidates` list with sub-scores and `current_candidate_url`.
* **Responsible File**: [`src/workflow.py: rank_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L972-L1000), [`src/tools.py: rank_sds_candidates`](file:///C:/Coding/Projects/L2/src/tools.py#L194-L372).
* **Next Stage**: Routes back to `decide_action_node` to validate the `FETCH` action.

---

### Stage 5: Document Fetching Behind Security & MCP Boundary (`fetch_node`)

* **Input**: `current_candidate_url` and optional `mcp_client`.
* **Processing**:
  1. Adds candidate URL to `fetched_urls` tracking list.
  2. **Path 1: MCP Subprocess Boundary** (Primary):
     - If `mcp_client.is_tool_available("inspect_sds_document")` is True:
     - Calls `await mcp_client.inspect_sds_document(target_url)` over stdio protocol.
     - FastMCP server runs in isolated child process, executes `safe_fetch_document`, parses document, and returns structured JSON evidence.
  3. **Path 2: Native Fallback**:
     - If MCP client is unavailable, invokes `safe_fetch_document` directly.
  4. **SSRF Network Shield Enforcement** ([`src/security.py`](file:///C:/Coding/Projects/L2/src/security.py)):
     - Validates scheme (HTTP/HTTPS only).
     - Resolves hostname via `socket.getaddrinfo`.
     - Inspects resolved IP against `BLOCKED_IP_NETWORKS` (RFC 1918 private IPs, loopback `127.0.0.0/8`, link-local/cloud metadata `169.254.0.0/16`, CGNAT, IPv6 ULA/link-local).
     - Enforces `SafeRedirectHandler`: re-validates DNS/IP on every redirect hop (max 5 hops).
     - Streams response in 64 KB chunks, enforcing strict 10 MB maximum document size limit (`MAX_DOCUMENT_SIZE_BYTES`).
  5. If fetch or parse fails or violates SSRF policy, records error in `failed_fetches[target_url]`.
  6. If successful, records structured `SDSEvidence` in `successful_fetches[target_url]`.
* **Output**: Updated `successful_fetches` or `failed_fetches`.
* **Responsible File**: [`src/workflow.py: fetch_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L1002-L1094), [`src/security.py`](file:///C:/Coding/Projects/L2/src/security.py), [`src/mcp_server.py`](file:///C:/Coding/Projects/L2/src/mcp_server.py#L109-L138).
* **Routing Decision** (`route_fetch`):
  - If a valid SDS document has been successfully fetched: routes to `draft_decision_node`.
  - If unvisited candidates remain and fetch count < 3: routes to `decide_action_node` to fetch next candidate.
  - Otherwise: routes to `draft_decision_node`.

---

### Stage 6: Multi-Format Document Parsing & Information Extraction

* **Input**: Raw bytes, `content_type`, and `final_url` from `safe_fetch_document`.
* **Processing**:
  1. Determines format: PDF vs. HTML.
  2. **PDF Parsing via PyMuPDF (`fitz`)**:
     - Opens byte stream in memory (`fitz.open(stream=raw_data, filetype="pdf")`).
     - Reads up to first 10 pages (`max_pdf_pages=10`).
     - Extracts clean text from each page and concatenates.
  3. **HTML Parsing via BeautifulSoup4**:
     - Decomposes script, style, nav, and footer elements.
     - Extracts visible body text.
  4. **GHS Section Extraction** (`extract_sds_sections`):
     - Applies regex patterns to split document into standard 16 GHS sections (Section 1 Identification, Section 2 Hazards, Section 3 Composition, Section 14 Transport, Section 15 Regulatory, etc.).
  5. **Chemical Entity Extraction**:
     - CAS numbers via `CAS_REGEX` (`\b[1-9]\d{1,6}-\d{2}-\d\b`).
     - Part/Catalog numbers via `PART_NUMBER_REGEX`.
     - Revision dates via `DATE_REGEX`.
     - Product Name & Manufacturer from Section 1 headers and document title patterns.
  6. **Language & Jurisdiction Detection**:
     - Language detected from structural header keywords (German, French, Spanish, Italian, Dutch, English).
     - Jurisdiction detected from Section 15 regulatory standards (OSHA/HCS 2012 for US, WHMIS for Canada, REACH/CLP for EU/UK).
* **Output**: Structured `SDSEvidence` Pydantic model (`url`, `product_name`, `manufacturer`, `cas_numbers`, `part_numbers`, `revision_date`, `language`, `country`, `is_sds`, `sections`, `url_type`, `fetched_successfully`).
* **Responsible File**: [`src/sds_parser.py: parse_sds_document`](file:///C:/Coding/Projects/L2/src/sds_parser.py#L214-L324).
* **Data Structure**: `SDSEvidence`.

---

### Stage 7: Stage B Document-First Scoring & Draft Verdict (`draft_decision_node`)

* **Input**: `successful_fetches` containing parsed `SDSEvidence` for all fetched documents.
* **Processing**:
  1. Scores each fetched document via `score_document_evidence` ([`src/tools.py`](file:///C:/Coding/Projects/L2/src/tools.py#L374-L484)):
     - Structure Score (0–25): Genuine GHS/OSHA headers.
     - Product Evidence Score (0–35): Chemical match in Section 1 or document text.
     - Manufacturer Evidence Score (0–30): Official domain or supplier match in Section 1.
     - CAS / Part Number Score (0–15): Identifier confirmed in Section 3.
     - Jurisdiction & Language Match (0–10).
     - Format Score (0–5): Direct PDF vs. landing page.
  2. Selects highest-scoring candidate document.
  3. Evaluates core compliance predicates: `is_sds`, `prod_match`, `comp_match`, `is_aggregator`.
  4. Sets draft status:
     - Official domain + PDF + exact chemical -> `EXACT MATCH` (confidence 85–98%).
     - Secondary trusted distributor or landing page -> `BEST AVAILABLE` (confidence 75–85%).
     - Compliance failure or aggregator -> `NEEDS REVIEW` (confidence 10–40%, URL cleared).
* **Output**: `draft_decision` dictionary (`status`, `confidence`, `detailed_reasoning`, `final_url`).
* **Responsible File**: [`src/workflow.py: draft_decision_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L1096-L1218).
* **Next Stage**: Stage 8 (`verify_decision_node`).

---

### Stage 8: Independent Reflection & Programmatic Verification (`verify_decision_node`)

* **Input**: `draft_decision`, `row_data`, `discovered_candidates`, `successful_fetches`, `failed_fetches`.
* **Processing** via `perform_verification` ([`src/workflow.py`](file:///C:/Coding/Projects/L2/src/workflow.py#L170-L450)):
  1. **SSRF Defense Check**: Rejects any request row containing loopback/private IPs with immediate `NEEDS REVIEW` and confidence 0.
  2. **Grounding Invariant Check**:
     - Checks if `draft_url` exists in `discovered_candidates` (URL provenance).
     - Checks if `draft_url` was successfully fetched and parsed.
     - If not grounded, logs grounding issue and forces downgrade to `NEEDS REVIEW`.
  3. **Independent Evidence Re-Verification**:
     - Product identity re-verified against raw extracted text tokens (does not trust model assertions).
     - Manufacturer re-verified against Section 1 supplier details or authorized domains.
     - Aggregator domain check: aggregator URLs are rejected with `NEEDS REVIEW`.
     - Non-SDS documents rejected with `NEEDS REVIEW`.
  4. **Strict Status Invariants**:
     - `EXACT MATCH`: Requires non-empty URL, confidence >= 50, official manufacturer or authorized domain, verified chemical match, direct PDF.
     - `BEST AVAILABLE`: Requires non-empty URL, confidence >= 30, verified chemical match from secondary portal or variant jurisdiction/language.
     - `NEEDS REVIEW`: Requires `final_url == ""`. Any ungrounded or failed candidate is forced to an empty URL.
* **Output**: Structured `VerificationResult` Pydantic model (`approved`, `issues`, `corrections`, `final_status`, `final_url`, `confidence`, `reasoning`, `product_match`, `manufacturer_match`, `jurisdiction_match`, `language_match`).
* **Responsible File**: [`src/workflow.py: verify_decision_node & perform_verification`](file:///C:/Coding/Projects/L2/src/workflow.py#L170-L450, #L1220-L1256).
* **Routing Decision** (`route_verification`):
  - If `verification_result["approved"]` is False: routes to `corrective_action_node`.
  - If `approved` is True: routes to `extract_final_node`.

---

### Stage 9: Corrective Action Node (`corrective_action_node`)

* **Input**: State with `verification_result` containing detected discrepancies or corrections.
* **Processing**:
  1. Overwrites draft status with verified `final_status`.
  2. Overwrites draft URL with verified `final_url` (empty string if status is `NEEDS REVIEW`).
  3. Calibrates confidence score to grounded value.
  4. Replaces draft reasoning with detailed explanation citing verification findings.
* **Output**: Corrected `draft_decision` state dictionary.
* **Responsible File**: [`src/workflow.py: corrective_action_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L1257-L1272).
* **Next Stage**: Stage 10 (`extract_final_node`).

---

### Stage 10: Final Extraction, Schema Validation & Provenance Construction (`extract_final_node`)

* **Input**: Fully verified verdict from verification/corrective nodes and complete state history.
* **Processing**:
  1. Constructs comprehensive `provenance` metadata:
     - `selected_url`, `url_type`, `discovered_candidates_count`, `successful_fetches_count`, `failed_fetches`.
     - `discovered_candidates_summary`: top 5 candidates with scores and reasons.
     - `mcp_tools_discovered`: tools discovered on MCP server.
     - `verified_at`: ISO timestamp.
     - `sections_extracted`: list of extracted GHS section names.
     - `product_matched`, `manufacturer_matched`, `jurisdiction_matched`, `language_matched`.
     - `verification_issues`: audit issues identified during reflection.
     - `review_category`: classified reason for `NEEDS REVIEW` (`SECURITY_REJECTION`, `UNTRUSTED_SOURCE`, `WRONG_PRODUCT`, `WRONG_MANUFACTURER`, `WRONG_COUNTRY_JURISDICTION`, `WRONG_LANGUAGE`, `NO_VALID_DOCUMENT`, `INSUFFICIENT_EVIDENCE`).
     - `action_sequence`: list of executed actions (`SEARCH`, `RANK`, `FETCH`, etc.).
     - `executed_queries`: search queries sent to search engine.
     - `ranking_sub_scores`: detailed Stage A score breakdown.
  2. Instantiates and validates `SDSValidationResult` Pydantic model:
     - Enforces status literal (`EXACT MATCH`, `BEST AVAILABLE`, `NEEDS REVIEW`).
     - Enforces confidence integer (0–100).
     - Enforces non-empty URL for positive verdicts; enforces empty URL for `NEEDS REVIEW`.
     - Enforces minimum reasoning length (5–2500 chars).
* **Output**: Final `SDSValidationResult` state dictionary.
* **Responsible File**: [`src/workflow.py: extract_final_node`](file:///C:/Coding/Projects/L2/src/workflow.py#L1273-L1402), [`src/schema.py: SDSValidationResult`](file:///C:/Coding/Projects/L2/src/schema.py#L170-L228).
* **Next Stage**: Graph terminal (`END`). Returns final state dictionary to caller.

---

### Stage 11: In-Place Excel Writeback & Audit Telemetry Logging

* **Input**: Final validated result from StateGraph, row index, and target file path.
* **Processing**:
  1. **In-Place Excel Update via FastMCP**:
     - Caller invokes `await mcp_client.update_request_status(...)`.
     - MCP server loads target workbook with `openpyxl`.
     - Locates or adds result columns: `Found URL`, `Status`, `Confidence`, `Reasoning`.
     - Writes values directly to target worksheet at physical row `excel_row`.
     - Saves workbook in-place.
  2. **Audit Telemetry Persistence**:
     - `server.py` serializes complete trace record to `logs/agent_trace.jsonl`:
       - `id`: UUIDv4
       - `timestamp`: UTC ISO timestamp
       - `request`: original input row
       - `final_status`, `final_url`, `confidence`, `detailed_reasoning`
       - `verification_result`: complete verification dictionary
       - `provenance`: complete provenance dictionary
       - `messages`: serialized conversational messages
* **Output**: Updated Excel file and appended JSONL audit log.
* **Responsible File**: [`src/mcp_server.py: update_request_status`](file:///C:/Coding/Projects/L2/src/mcp_server.py#L67-L108), [`server.py`](file:///C:/Coding/Projects/L2/server.py#L490-L520).
* **Next Stage**: Stage 12 (Frontend Presentation).

---

### Stage 12: Real-Time User Interface Presentation

* **Input**: HTTP response from API endpoints (`/api/sds/search`, `/api/batch/status`, `/api/stats`, `/api/history`, `/api/review`).
* **Processing**:
  1. **Single Search Page**:
     - Renders result card with status badge (`EXACT MATCH` in emerald, `BEST AVAILABLE` in amber, `NEEDS REVIEW` in rose).
     - Renders confidence gauge, direct PDF download button, reasoning citation, and expandable provenance inspector.
  2. **Batch Processing Page**:
     - Displays live progress bar (`completed_requests / total_requests`), current processing chemical, and real-time results table.
     - Provides Excel export button (`/api/batch/export`).
  3. **Dashboard Page**:
     - Telemetry cards showing total queries, exact matches, best available, needs review count, average confidence.
     - Interactive Recharts breakdown: status distribution, latency trends.
  4. **Review Queue Page**:
     - Filters requests flagged as `NEEDS REVIEW`.
     - Displays classified review category and specific compliance issues identified by the verification stage.
  5. **Agent Trace Page**:
     - Displays latest execution trace, LangGraph node sequence, model latency, and MCP tool discovery logs.
* **Output**: Interactive command center view for evaluators and compliance officers.
* **Responsible File**: [`frontend/src/pages/`](file:///C:/Coding/Projects/L2/frontend/src/pages/), [`frontend/src/components/`](file:///C:/Coding/Projects/L2/frontend/src/components/).

---

## 3. Data Flow & Transformation Summary Table

| Stage | Input Data | Primary Data Structure | Output Data | Transformation Logic |
|---|---|---|---|---|
| **0. Ingestion** | User form or `.xlsx` sheet | `dict` / `pd.DataFrame` | Clean request row | Semantic column mapping + worksheet classification |
| **1. State Seed** | Clean request row | `SDSState` (TypedDict) | Seed state | State dictionary initialized with empty collections |
| **2. Action Selection** | Current `SDSState` | `ActionDecision` (Pydantic) | `next_action`, target query/URL | LLM policy consultation + deterministic prerequisite guards |
| **3. Search** | Target query string | `list[dict]` from `DDGS` | `discovered_candidates` | Web query + manufacturer official domain lookup |
| **4. Ranking** | `discovered_candidates` | Ranked `list[dict]` | `ranked_candidates` | Stage A metadata heuristic scoring (0–100) |
| **5. Fetching** | `current_candidate_url` | Raw `bytes` + headers | `successful_fetches` / `failed_fetches` | SSRF network shield + FastMCP stdio subprocess |
| **6. Parsing** | Raw `bytes` (PDF/HTML) | `SDSEvidence` (Pydantic) | Structured document fields | PyMuPDF text extraction, regex, GHS section split |
| **7. Draft Verdict** | `SDSEvidence` pool | `dict` (`draft_decision`) | Draft status, confidence, URL | Stage B document-first evidence scoring (0–100) |
| **8. Verification** | Draft verdict + evidence | `VerificationResult` (Pydantic) | Grounded verification result | SSRF check + grounding invariants + evidence cross-check |
| **9. Correction** | Discrepancies list | `dict` (`draft_decision`) | Corrected draft verdict | Downgrading, URL clearance, confidence adjustment |
| **10. Extraction** | Verified result + state | `SDSValidationResult` (Pydantic) | Final validated result | Schema validation, provenance assembly, review classification |
| **11. Writeback** | Final result + row index | `openpyxl.Workbook` + JSONL | Updated `.xlsx` + `agent_trace.jsonl` | FastMCP Excel writeback + persistent audit trail |
| **12. Presentation** | API JSON responses | React Query state | Interactive Dark Theme UI | Real-time dashboards, charts, review drawer, trace view |
