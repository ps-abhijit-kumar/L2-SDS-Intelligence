import pytest
from unittest.mock import MagicMock
from src.workflow import (
    create_sds_graph,
    decide_action_node,
    route_action,
    perform_verification,
    format_policy_context
)
from src.schema import ActionDecision
from src.state import SDSState

def test_graph_compilation():
    graph = create_sds_graph()
    assert graph is not None
    node_names = list(graph.nodes.keys())
    assert "decide_action" in node_names
    assert "search" in node_names
    assert "rank" in node_names
    assert "fetch" in node_names
    assert "draft" in node_names
    assert "verify" in node_names
    assert "correct" in node_names
    assert "extract_final" in node_names

def test_llm_policy_chooses_search():
    """Test 1: LLM policy receives empty candidate observation and decides SEARCH."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_decision = ActionDecision(
        action="SEARCH",
        reason="No candidates discovered yet. Initiating search with primary 4 fields."
    )
    mock_structured.invoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured

    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "Language": "English", "Country": "United States"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "action_history": [],
        "next_action": None,
        "iteration_count": 0,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }

    result = decide_action_node(state, llm=mock_llm)
    assert mock_structured.invoke.called
    assert result["next_action"] == "SEARCH"
    assert "SEARCH" in result["action_history"][-1]["action"]

def test_llm_policy_search_observation_chooses_fetch():
    """Test 2: LLM policy receives search candidates observation and chooses FETCH on target candidate."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_decision = ActionDecision(
        action="FETCH",
        target_url="https://sigma.com/acetone_sds.pdf",
        reason="Discovered candidate is a direct PDF from manufacturer matching product identity."
    )
    mock_structured.invoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured

    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "Language": "English", "Country": "United States"},
        "discovered_candidates": [
            {"url": "https://sigma.com/acetone_sds.pdf", "title": "Acetone SDS", "snippet": "Safety Data Sheet"}
        ],
        "ranked_candidates": [
            {"url": "https://sigma.com/acetone_sds.pdf", "score": 95, "title": "Acetone SDS", "snippet": "Safety Data Sheet"}
        ],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "action_history": [{"action": "SEARCH", "reason": "Executed initial search"}],
        "next_action": None,
        "iteration_count": 1,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }

    result = decide_action_node(state, llm=mock_llm)
    assert mock_structured.invoke.called
    assert result["next_action"] == "FETCH"
    assert result["current_candidate_url"] == "https://sigma.com/acetone_sds.pdf"

def test_llm_policy_strong_evidence_chooses_finish():
    """Test 3: Given strong fetched evidence matching product and company, LLM chooses FINISH."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_decision = ActionDecision(
        action="FINISH",
        reason="Grounded evidence confirms exact product name, manufacturer, and authentic GHS safety sections."
    )
    mock_structured.invoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured

    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "Language": "English", "Country": "United States"},
        "discovered_candidates": [{"url": "https://sigma.com/acetone_sds.pdf"}],
        "ranked_candidates": [{"url": "https://sigma.com/acetone_sds.pdf", "score": 95}],
        "fetched_urls": ["https://sigma.com/acetone_sds.pdf"],
        "successful_fetches": {
            "https://sigma.com/acetone_sds.pdf": {
                "url": "https://sigma.com/acetone_sds.pdf",
                "is_sds": True,
                "product_name": "Acetone",
                "manufacturer": "Sigma-Aldrich",
                "raw_snippet": "Acetone Safety Data Sheet Sigma-Aldrich Section 1 Identification",
                "sections": {"1": "Identification", "2": "Hazard(s) Identification"}
            }
        },
        "failed_fetches": {},
        "current_candidate_url": "https://sigma.com/acetone_sds.pdf",
        "action_history": [
            {"action": "SEARCH", "reason": "Searched candidates"},
            {"action": "FETCH", "target_url": "https://sigma.com/acetone_sds.pdf", "reason": "Fetched document"}
        ],
        "next_action": None,
        "iteration_count": 2,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }

    result = decide_action_node(state, llm=mock_llm)
    assert mock_structured.invoke.called
    assert result["next_action"] == "FINISH"

def test_llm_policy_fetch_failure_chooses_retry():
    """Test 4: Given a failed fetch observation, LLM chooses an alternative candidate / RETRY."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_decision = ActionDecision(
        action="RETRY",
        target_url="https://thermofisher.com/acetone_alt.pdf",
        reason="Primary candidate 404 failed. Retrying with alternative candidate."
    )
    mock_structured.invoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured

    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "Language": "English", "Country": "United States"},
        "discovered_candidates": [
            {"url": "https://broken-link.com/sds.pdf"},
            {"url": "https://thermofisher.com/acetone_alt.pdf"}
        ],
        "ranked_candidates": [
            {"url": "https://broken-link.com/sds.pdf", "score": 90},
            {"url": "https://thermofisher.com/acetone_alt.pdf", "score": 85}
        ],
        "fetched_urls": ["https://broken-link.com/sds.pdf"],
        "successful_fetches": {},
        "failed_fetches": {"https://broken-link.com/sds.pdf": "404 Not Found"},
        "current_candidate_url": "https://broken-link.com/sds.pdf",
        "action_history": [
            {"action": "SEARCH", "reason": "Discovered candidates"},
            {"action": "FETCH", "target_url": "https://broken-link.com/sds.pdf", "reason": "Attempted first fetch"}
        ],
        "next_action": None,
        "iteration_count": 2,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }

    result = decide_action_node(state, llm=mock_llm)
    assert mock_structured.invoke.called
    assert result["next_action"] == "FETCH"
    assert result["current_candidate_url"] == "https://thermofisher.com/acetone_alt.pdf"
    assert result["retry_count"] == 1

def test_llm_policy_invalid_action_rejected_by_guard():
    """Test 5: Invalid/unsupported action or ungrounded fabricated URL is intercepted by deterministic Python guard."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    # Model attempts to hallucinate an ungrounded URL not present in discovered candidates
    mock_decision = ActionDecision(
        action="FETCH",
        target_url="https://malicious-or-invented-domain.com/fake.pdf",
        reason="Fabricated URL not in discovered candidates."
    )
    mock_structured.invoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured

    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma"},
        "discovered_candidates": [{"url": "https://sigma.com/legitimate_sds.pdf"}],
        "ranked_candidates": [{"url": "https://sigma.com/legitimate_sds.pdf", "score": 90}],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "action_history": [],
        "next_action": None,
        "iteration_count": 1,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }

    result = decide_action_node(state, llm=mock_llm)
    # The guard intercepts the ungrounded URL and replaces it with the valid unvisited candidate
    assert result["next_action"] == "FETCH"
    assert result["current_candidate_url"] == "https://sigma.com/legitimate_sds.pdf"
    assert result["current_candidate_url"] != "https://malicious-or-invented-domain.com/fake.pdf"

def test_terminal_path_routes_through_verification():
    """Test 6: Verify route_action sends FINISH to draft and verify rather than bypassing verification."""
    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "action_history": [],
        "next_action": "FINISH",
        "iteration_count": 6,
        "retry_count": 2,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }
    routed_target = route_action(state)
    assert routed_target == "draft"  # Routes to draft -> verify -> extract_final

def test_loop_boundedness_and_iteration_limit():
    state: SDSState = {
        "messages": [],
        "row_data": {},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "action_history": [],
        "next_action": None,
        "iteration_count": 7,  # Exceeded limit
        "retry_count": 3,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "ERROR",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }
    decision = decide_action_node(state)
    assert decision["next_action"] == "FINISH"
