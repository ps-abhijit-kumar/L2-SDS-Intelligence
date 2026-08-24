import pytest
from src.workflow import (
    create_sds_graph,
    decide_action_node,
    route_action,
    perform_verification
)
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

def test_dynamic_action_selection_path_a():
    # Initial state -> SEARCH
    state_0: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Company": "Sigma"},
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
        "final_status": "ERROR",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }
    step_1 = decide_action_node(state_0)
    assert step_1["next_action"] == "SEARCH"

    # Candidates discovered -> RANK
    state_1 = dict(state_0)
    state_1["discovered_candidates"] = [{"url": "https://sigma.com/doc.pdf"}]
    step_2 = decide_action_node(state_1)
    assert step_2["next_action"] == "RANK"

    # Candidates ranked -> FETCH
    state_2 = dict(state_1)
    state_2["ranked_candidates"] = [{"url": "https://sigma.com/doc.pdf", "score": 90}]
    step_3 = decide_action_node(state_2)
    assert step_3["next_action"] == "FETCH"
    assert step_3["current_candidate_url"] == "https://sigma.com/doc.pdf"

    # Candidate fetched -> DRAFT
    state_3 = dict(state_2)
    state_3["fetched_urls"] = ["https://sigma.com/doc.pdf"]
    state_3["successful_fetches"] = {"https://sigma.com/doc.pdf": {"is_sds": True, "raw_snippet": "Acetone SDS", "sections": {}}}
    step_4 = decide_action_node(state_3)
    assert step_4["next_action"] == "DRAFT"

def test_dynamic_action_selection_retry_path():
    # Verification failed with unvisited candidates remaining -> RETRY / FETCH next
    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Company": "Sigma"},
        "discovered_candidates": [{"url": "https://c1.com/sds.pdf"}, {"url": "https://c2.com/sds.pdf"}],
        "ranked_candidates": [{"url": "https://c1.com/sds.pdf", "score": 80}, {"url": "https://c2.com/sds.pdf", "score": 75}],
        "fetched_urls": ["https://c1.com/sds.pdf"],
        "successful_fetches": {"https://c1.com/sds.pdf": {"is_sds": False, "raw_snippet": "Not an SDS", "sections": {}}},
        "failed_fetches": {},
        "current_candidate_url": "https://c1.com/sds.pdf",
        "action_history": [],
        "next_action": None,
        "iteration_count": 2,
        "retry_count": 0,
        "draft_decision": {"status": "EXACT MATCH", "final_url": "https://c1.com/sds.pdf", "confidence": 80, "detailed_reasoning": "Draft"},
        "verification_result": {"approved": False, "issues": ["Document not SDS"], "final_status": "NEEDS REVIEW"},
        "final_status": "ERROR",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None
    }
    decision = decide_action_node(state)
    assert decision["next_action"] == "FETCH"
    assert decision["current_candidate_url"] == "https://c2.com/sds.pdf"
    assert decision["retry_count"] == 1

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
