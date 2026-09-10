"""
LangGraph Agent State Definition
================================
Architecture Role:
    Defines the centralized channel schema (SDSState TypedDict) that flows through
    all nodes and conditional edges in the LangGraph agent state machine.

State Channels & Lifecycle:
    1. Conversational Messages:
       Uses LangGraph's `add_messages` reducer to maintain an append-only trace
       of Human, AI, and System tool-interaction messages.
    2. Input Context (row_data):
       The target chemical search request extracted from user Excel sheets or single search API.
    3. Retrieval & Candidate Discovery:
       Tracks raw candidates discovered via search, ranked candidates prioritized by domain tier,
       and fetch history (successful extractions vs transient/permanent failures).
    4. Adaptive Multi-Query Retry Tracking:
       Maintains list of previously executed search queries to prevent duplicates
       and iteration/retry counters enforcing termination bounds.
    5. Independent Reflection & Verification:
       Stores draft decisions and rigorous 4-checkpoint verification results.
    6. Final Structured Verdict:
       Carries final status, grounded URL, confidence score, detailed reasoning,
       and provenance metadata for database/Excel persistence.
    7. MCP Subsystem Integration:
       Optionally holds reference to connected SDSMCPClient for stdio-isolated tool operations.
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class SDSState(TypedDict):
    # LangGraph conversational / ReAct message stream
    messages: Annotated[List[AnyMessage], add_messages]

    # Request Input Context
    row_data: Dict[str, Any]

    # Provenance and Discovery State (Priority 4)
    discovered_candidates: List[Dict[str, Any]]
    ranked_candidates: List[Dict[str, Any]]
    fetched_urls: List[str]
    successful_fetches: Dict[str, Dict[str, Any]]
    failed_fetches: Dict[str, str]
    current_candidate_url: str

    # Agentic Search & Adaptive Retry State (Phases 2 & 3)
    search_queries: List[str]
    current_search_query: Optional[str]

    # Dynamic Action State (Priority 3 & Phase 4)
    action_history: List[Dict[str, Any]]
    next_action: Optional[str]
    iteration_count: int
    retry_count: int

    # Reflection & Independent Verification State (Priority 1)
    draft_decision: Optional[Dict[str, Any]]
    verification_result: Optional[Dict[str, Any]]

    # Strict Structured Final Verdict (Priority 2 & Phase 6)
    final_status: str
    final_url: str
    url_type: Optional[str]
    confidence: int
    detailed_reasoning: str
    provenance: Optional[Dict[str, Any]]

    # MCP Client boundary integration (Phase 1 & 8)
    mcp_client: Optional[Any]
