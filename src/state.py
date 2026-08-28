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
