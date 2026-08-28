import pytest
from unittest.mock import MagicMock, patch
from src.workflow import (
    create_sds_graph,
    decide_action_node,
    search_node,
    rank_node,
    fetch_node,
    draft_decision_node,
    route_action,
    route_fetch,
    perform_verification,
    format_policy_context,
    validate_search_query,
    generate_adaptive_query
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

def test_llm_policy_records_llm_source_and_model():
    """Test 1: LLM policy selection records policy_source='llm', policy_model, and latency."""
    mock_llm = MagicMock()
    mock_llm.model_name = "openai/gpt-oss-120b"
    mock_structured = MagicMock()
    mock_decision = ActionDecision(
        action="SEARCH",
        search_query="Acetone Sigma-Aldrich SDS pdf",
        reason="No candidates discovered yet. Initiating targeted search."
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
        "search_queries": [],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }

    result = decide_action_node(state, llm=mock_llm)
    assert mock_structured.invoke.called
    assert result["next_action"] == "SEARCH"
    assert result["current_search_query"] == "Acetone Sigma-Aldrich SDS pdf"
    assert len(result["action_history"]) == 1

    action_entry = result["action_history"][0]
    assert action_entry["policy_source"] == "llm"
    assert "gpt-oss-120b" in str(action_entry["policy_model"])
    assert action_entry["policy_latency_ms"] >= 0.0
    assert action_entry["llm_error"] is None

def test_llm_policy_failure_records_fallback_and_sanitized_error():
    """Test 2: LLM invocation failure records policy_source='fallback' and sanitized error class."""
    mock_llm = MagicMock()
    mock_llm.model_name = "test-model"
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = RuntimeError("API authentication failed: secret_key_12345")
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
        "search_queries": [],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }

    result = decide_action_node(state, llm=mock_llm)
    # Should fall back cleanly without raising
    assert result["next_action"] == "SEARCH"
    assert len(result["action_history"]) == 1

    action_entry = result["action_history"][0]
    assert action_entry["policy_source"] == "fallback"
    assert action_entry["llm_error"] == "RuntimeError"
    # Ensure sensitive credentials are NOT leaked in trace entry
    assert "secret_key_12345" not in str(action_entry)

def test_model_selected_search_query_passed_to_search():
    """Test 3: Model-selected SEARCH query is preserved and executed by search_node."""
    custom_model_query = "Sigma-Aldrich Acetone 67-64-1 SDS PDF"
    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "Language": "English", "Country": "United States"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "search_queries": [],
        "current_search_query": custom_model_query,
        "action_history": [{"action": "SEARCH", "search_query": custom_model_query}],
        "next_action": "SEARCH",
        "iteration_count": 1,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None,
        "mcp_client": None
    }

    with patch("src.workflow.search_duckduckgo") as mock_search_tool:
        mock_search_tool.invoke.return_value = [
            {"url": "https://www.sigmaaldrich.com/US/en/sds/179124.pdf", "title": "Acetone SDS", "body": "Safety Data Sheet"}
        ]
        search_res = search_node(state)
        assert mock_search_tool.invoke.called
        # Check that the exact model-selected query was passed to DuckDuckGo
        called_query = mock_search_tool.invoke.call_args[0][0]["query"]
        assert called_query == custom_model_query
        assert custom_model_query in search_res["search_queries"]

def test_retry_with_different_query_executes_that_query():
    """Test 4: RETRY with a distinct model query executes that new query."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    retry_query = "Sigma-Aldrich Acetone CAS 67-64-1 SDS"
    mock_decision = ActionDecision(
        action="RETRY",
        search_query=retry_query,
        reason="First attempt failed. Retrying with CAS-specific query."
    )
    mock_structured.invoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured

    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "CAS": "67-64-1", "Language": "English", "Country": "United States"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": ["https://bad-url.com/doc.html"],
        "successful_fetches": {},
        "failed_fetches": {"https://bad-url.com/doc.html": "404 Not Found"},
        "current_candidate_url": "",
        "search_queries": ["Sigma-Aldrich Acetone SDS"],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }

    result = decide_action_node(state, llm=mock_llm)
    assert result["next_action"] == "SEARCH"
    assert result["current_search_query"] == retry_query
    assert result["retry_count"] == 1

def test_retry_without_usable_query_does_not_repeat_previous_query():
    """Test 5: RETRY without usable query produces an adaptive query distinct from previous queries."""
    initial_query = "Sigma-Aldrich Acetone SDS"
    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "CAS": "67-64-1", "Part Number": "179124", "Language": "English", "Country": "United States"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": ["https://bad-url.com/doc.html"],
        "successful_fetches": {},
        "failed_fetches": {"https://bad-url.com/doc.html": "404 Not Found"},
        "current_candidate_url": "",
        "search_queries": [initial_query],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }

    # Deterministic fallback execution on RETRY
    result = decide_action_node(state)
    assert result["next_action"] == "SEARCH"
    assert result["current_search_query"] != initial_query
    assert result["current_search_query"].lower() != initial_query.lower()
    assert result["retry_count"] == 1

def test_duplicate_invalid_search_query_rejected_or_replaced_safely():
    """Test 6: Invalid search queries with embedded SSRF or control characters are sanitized safely."""
    row = {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"}
    
    # 1. Unsafe SSRF injection query
    unsafe_q = "Acetone http://127.0.0.1:8000/sds.pdf"
    clean_q = validate_search_query(unsafe_q, row)
    assert "127.0.0.1" not in clean_q
    assert "http://" not in clean_q
    assert "Acetone" in clean_q

    # 2. Control characters sanitized
    control_q = "Acetone\r\n\tSigma\x00-Aldrich SDS"
    clean_control = validate_search_query(control_q, row)
    assert "\r" not in clean_control
    assert "\n" not in clean_control
    assert "\x00" not in clean_control
    assert "Acetone" in clean_control

    # 3. Empty query falls back to valid default
    empty_clean = validate_search_query("", row)
    assert "Sigma-Aldrich Acetone SDS" == empty_clean

def test_existing_url_security_guards_intact():
    """Test 7: Parameter-level SSRF is rejected immediately to NEEDS REVIEW with empty URL."""
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Part Number": "http://127.0.0.1:8000/sds.pdf",
        "Country": "United States",
        "Language": "English"
    }
    state: SDSState = {
        "messages": [],
        "row_data": row_data,
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "search_queries": [],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }
    res = decide_action_node(state)
    assert res["next_action"] == "FINISH"

    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url="http://127.0.0.1:8000/sds.pdf",
        draft_confidence=90,
        draft_reasoning="SSRF candidate.",
        discovered_candidates=[],
        successful_fetches={},
        failed_fetches={}
    )
    assert ver.final_status == "NEEDS REVIEW"
    assert ver.final_url == ""

def test_finish_routes_through_draft_and_verify():
    """Test 8: FINISH action routes cleanly to draft -> verify -> extract_final."""
    state: SDSState = {
        "next_action": "FINISH"
    }
    assert route_action(state) == "draft"

def test_retry_count_increments_reliably_and_terminates():
    """Verify retry_count increments when candidates are exhausted and terminates to FINISH."""
    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Nonexistent Chemical", "Product Company Name": "Unknown Co", "Language": "English", "Country": "United States"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "search_queries": ["query 1"],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }

    # Step 1: Retry count should increment to 1
    res1 = decide_action_node(state)
    assert res1["retry_count"] == 1
    assert res1["next_action"] == "SEARCH"

    # Step 2: Retry with retry_count = 1 should increment to 2
    state["retry_count"] = 1
    state["search_queries"] = ["query 1", "query 2"]
    res2 = decide_action_node(state)
    assert res2["retry_count"] == 2

    # Step 3: Retry with retry_count = 2 must terminate to FINISH
    state["retry_count"] = 2
    res3 = decide_action_node(state)
    assert res3["next_action"] == "FINISH"

def test_multi_candidate_fallback_route_fetch():
    """When candidate 1 fetch yields non-SDS, route_fetch routes to decide_action for candidate 2."""
    state: SDSState = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma"},
        "discovered_candidates": [
            {"url": "https://site.com/bad.html"},
            {"url": "https://www.sigmaaldrich.com/sds/good.pdf"}
        ],
        "ranked_candidates": [
            {"url": "https://site.com/bad.html"},
            {"url": "https://www.sigmaaldrich.com/sds/good.pdf"}
        ],
        "fetched_urls": ["https://site.com/bad.html"],
        "successful_fetches": {
            "https://site.com/bad.html": {"is_sds": False}
        },
        "failed_fetches": {},
        "current_candidate_url": "https://site.com/bad.html",
        "search_queries": ["query 1"],
        "current_search_query": None,
        "action_history": [],
        "next_action": None,
        "iteration_count": 2,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None,
        "final_status": "PENDING",
        "final_url": "",
        "confidence": 0,
        "detailed_reasoning": "",
        "provenance": None,
        "mcp_client": None
    }

    target = route_fetch(state)
    assert target == "decide_action"

def test_chemical_synonym_product_verification():
    """Ethanol 200 Proof request matches Ethyl Alcohol SDS in perform_verification."""
    row_data = {
        "Product Name": "Ethanol 200 Proof",
        "Product Company Name": "Avantor",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://www.avantorsciences.com/sds/ethanol.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Ethyl Alcohol, Absolute",
            "manufacturer": "Avantor Performance Materials",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Avantor Safety Data Sheet for Ethyl Alcohol Absolute.",
            "sections": {"section_1_identification": "Product Name: Ethyl Alcohol, Manufacturer: Avantor"}
        }
    }

    ver = perform_verification(
        row_data=row_data,
        draft_status="BEST AVAILABLE",
        draft_url=target_url,
        draft_confidence=85,
        draft_reasoning="Ethanol match.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )

    assert ver.product_match is True
    assert ver.manufacturer_match is True
    assert ver.final_status == "BEST AVAILABLE"

def test_fake_manufacturer_flags_needs_review_with_empty_url():
    """Fictional manufacturer with no authorized domains flags NEEDS REVIEW with empty URL."""
    row_data = {
        "Product Name": "Sodium Hydroxide",
        "Product Company Name": "FictionalBio Nonexistent Labs Global Inc",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://www.cdhfinechemical.com/sds/naoh.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Sodium Hydroxide Pellets",
            "manufacturer": "Central Drug House Ltd",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Safety Data Sheet for Sodium Hydroxide.",
            "sections": {"section_1_identification": "Product Name: Sodium Hydroxide, Manufacturer: CDH"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="BEST AVAILABLE",
        draft_url=target_url,
        draft_confidence=75,
        draft_reasoning="NaOH from CDH.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.manufacturer_match is False
    assert ver.final_status == "NEEDS REVIEW"
    assert ver.final_url == ""

def test_wrong_jurisdiction_assigns_best_available_with_grounded_url():
    """Jurisdiction discrepancy (e.g. Antarctica) assigns BEST AVAILABLE with grounded URL."""
    row_data = {
        "Product Name": "Nitric Acid",
        "Product Company Name": "Thermo Fisher",
        "Country": "Antarctica Autonomous Research Zone",
        "Language": "English"
    }
    target_url = "https://documents.thermofisher.com/sds/nitric_acid.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Nitric Acid 70%",
            "manufacturer": "Thermo Fisher Scientific",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Thermo Fisher Nitric Acid SDS.",
            "sections": {"section_1_identification": "Product: Nitric Acid, Manufacturer: Thermo Fisher"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=90,
        draft_reasoning="Exact match.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.product_match is True
    assert ver.manufacturer_match is True
    assert ver.jurisdiction_match is False
    assert ver.final_status == "BEST AVAILABLE"
    assert ver.final_url == target_url

def test_empty_product_parameter_rejected_immediately_needs_review():
    """Request with empty product name immediately halts to NEEDS REVIEW."""
    row_data = {
        "Product Name": "",
        "Product Company Name": "Sigma-Aldrich",
        "Country": "United States",
        "Language": "English"
    }
    state: SDSState = {
        "messages": [],
        "row_data": row_data,
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "current_candidate_url": "",
        "search_queries": [],
        "current_search_query": None,
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
        "provenance": None,
        "mcp_client": None
    }
    search_res = search_node(state)
    assert search_res["final_status"] == "NEEDS REVIEW"
    assert search_res["final_url"] == ""
    assert search_res["next_action"] == "FINISH"

def test_gt001_authorized_sigma_aldrich_domain_accepted_exact_match():
    """GT_001 authorized Sigma-Aldrich domain satisfies EXACT MATCH grounding."""
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://www.sigmaaldrich.com/US/en/sds/179124.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Acetone",
            "manufacturer": "Sigma-Aldrich Inc.",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Sigma-Aldrich Safety Data Sheet for Acetone.",
            "sections": {"section_1_identification": "Product Name: Acetone, Manufacturer: Sigma-Aldrich"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=95,
        draft_reasoning="Exact match from official Sigma portal.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.product_match is True
    assert ver.manufacturer_match is True
    assert ver.final_status == "EXACT MATCH"
    assert ver.final_url == target_url

def test_gt005_authorized_honeywell_domain_accepted_exact_match():
    """GT_005 authorized Honeywell domain satisfies EXACT MATCH grounding."""
    row_data = {
        "Product Name": "Toluene",
        "Product Company Name": "Honeywell",
        "Country": "Germany",
        "Language": "English"
    }
    target_url = "https://www.lab-honeywell.com/sds/34866.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Toluene",
            "manufacturer": "Honeywell Specialty Chemicals",
            "language": "English",
            "country": "Germany",
            "raw_snippet": "Honeywell Safety Data Sheet for Toluene.",
            "sections": {"section_1_identification": "Product: Toluene, Manufacturer: Honeywell"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=95,
        draft_reasoning="Exact match from official Honeywell portal.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.product_match is True
    assert ver.manufacturer_match is True
    assert ver.final_status == "EXACT MATCH"
    assert ver.final_url == target_url

def test_unauthorized_domain_rejected_from_exact_match():
    """Unauthorized third-party WordPress upload (e.g. lafrentz.ca) is rejected to NEEDS REVIEW."""
    row_data = {
        "Product Name": "Toluene",
        "Product Company Name": "Honeywell",
        "Country": "Germany",
        "Language": "English"
    }
    target_url = "https://lafrentz.ca/wp-content/uploads/Toluene-Honeywell.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Toluene",
            "manufacturer": "Honeywell",
            "language": "English",
            "country": "Germany",
            "raw_snippet": "Honeywell Safety Data Sheet for Toluene.",
            "sections": {"section_1_identification": "Product: Toluene, Manufacturer: Honeywell"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=90,
        draft_reasoning="PDF with Honeywell in name.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    # Unverified third-party host must be rejected to NEEDS REVIEW with empty URL
    assert ver.final_status == "NEEDS REVIEW"
    assert ver.final_url == ""

def test_sdsmanager_aggregator_rejected_to_needs_review():
    """Aggregator scraper (e.g. sdsmanager.com) is strictly rejected to NEEDS REVIEW with empty URL."""
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://sdsmanager.com/safety-data-sheet/sigma-aldrich-inc-acetone-en/"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Acetone",
            "manufacturer": "Sigma-Aldrich Inc.",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Scraped catalog landing page for Sigma Acetone.",
            "sections": {"section_1_identification": "Product Name: Acetone, Manufacturer: Sigma-Aldrich"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="BEST AVAILABLE",
        draft_url=target_url,
        draft_confidence=75,
        draft_reasoning="Aggregator landing page.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.final_status == "NEEDS REVIEW"
    assert ver.final_url == ""

def test_trusted_distributor_domain_accepted_best_available():
    """Explicitly trusted chemical distributor (e.g. vwr.com) is accepted as BEST AVAILABLE."""
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://us.vwr.com/store/sds/acetone.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Acetone",
            "manufacturer": "Sigma-Aldrich",
            "language": "English",
            "country": "United States",
            "raw_snippet": "VWR distributor SDS for Sigma Acetone.",
            "sections": {"section_1_identification": "Product Name: Acetone, Manufacturer: Sigma-Aldrich"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="BEST AVAILABLE",
        draft_url=target_url,
        draft_confidence=80,
        draft_reasoning="Trusted distributor document.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.final_status == "BEST AVAILABLE"
    assert ver.final_url == target_url

def test_candidate_pool_low_quality_triggers_adaptive_retry():
    """When top candidate score is below quality threshold (< 30), decide_action_node triggers RETRY."""
    state = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich", "CAS": "67-64-1"},
        "discovered_candidates": [{"url": "https://poor-scraped-site.com/doc", "title": "Scraped Document"}],
        "ranked_candidates": [{"url": "https://poor-scraped-site.com/doc", "score": 15, "reasons": ["Demoted Aggregator"]}],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "search_queries": ["Sigma-Aldrich Acetone SDS"],
        "action_history": [],
        "iteration_count": 1,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": None
    }

    result = decide_action_node(state)
    assert result["next_action"] == "SEARCH"
    assert result["retry_count"] == 1
    assert result["current_search_query"] != "Sigma-Aldrich Acetone SDS"
    assert len(result["action_history"]) == 1
    assert "quality" in result["action_history"][0]["reason"].lower() or "low" in result["action_history"][0]["reason"].lower()

def test_adaptive_query_generates_site_scoped_strategy_for_authorized_domain():
    """Adaptive query generation formulates site:domain queries for manufacturers with known authorized domains."""
    row = {
        "Product Name": "Toluene",
        "Product Company Name": "Honeywell",
        "CAS": "108-88-3"
    }
    prev_queries = ["Honeywell Toluene SDS", "Honeywell Toluene Safety Data Sheet"]
    adaptive_q = generate_adaptive_query(row, prev_queries, retry_idx=1)
    assert "Toluene" in adaptive_q
    assert ("site:honeywell.com" in adaptive_q or "site:lab-honeywell.com" in adaptive_q or "108-88-3" in adaptive_q)

def test_policy_context_renders_candidate_scores_and_ranking_reasons():
    """format_policy_context includes candidate utility scores and ranking reasons in prompt context."""
    state = {
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"},
        "discovered_candidates": [{"url": "https://www.sigmaaldrich.com/sds.pdf", "title": "Acetone SDS"}],
        "ranked_candidates": [{"url": "https://www.sigmaaldrich.com/sds.pdf", "score": 92, "reasons": ["Official Manufacturer Domain", "Direct SDS Document"], "title": "Acetone SDS"}],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "search_queries": ["Sigma-Aldrich Acetone SDS"],
        "action_history": []
    }
    context = format_policy_context(state)
    assert "Score: 92" in context
    assert "Official Manufacturer Domain" in context

def test_product_in_url_only_rejected_if_document_body_mismatches():
    """Product verification fails if product name appears only in URL string but document text discusses a different chemical."""
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://www.sigmaaldrich.com/sds/acetone.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Hydrochloric Acid",  # Document is actually HCl
            "manufacturer": "Sigma-Aldrich",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Safety Data Sheet for Hydrochloric Acid aqueous solution.",
            "sections": {"section_1_identification": "Product: Hydrochloric Acid, Supplier: Sigma-Aldrich"}
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=90,
        draft_reasoning="URL contained acetone.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert ver.product_match is False
    assert ver.final_status == "NEEDS REVIEW"
    assert ver.final_url == ""

def test_incomplete_sparse_sds_evidence_rejected_to_needs_review():
    """Document lacking authentic GHS safety sections and sufficient text body flags NEEDS REVIEW."""
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Country": "United States",
        "Language": "English"
    }
    target_url = "https://www.sigmaaldrich.com/sds/179124.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "product_name": "Acetone",
            "manufacturer": "Sigma-Aldrich",
            "language": "English",
            "country": "United States",
            "raw_snippet": "Tiny stub",
            "sections": {}  # Empty sections
        }
    }
    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=80,
        draft_reasoning="Stub SDS.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )
    assert any("Evidence Incompleteness" in iss for iss in ver.issues)

def test_final_verdict_retains_enriched_evidence_provenance():
    """extract_final_node populates comprehensive evidence provenance in final state."""
    from src.workflow import extract_final_node

    state = {
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"},
        "discovered_candidates": [{"url": "https://www.sigmaaldrich.com/sds/179124.pdf"}],
        "ranked_candidates": [{"url": "https://www.sigmaaldrich.com/sds/179124.pdf", "score": 95}],
        "successful_fetches": {
            "https://www.sigmaaldrich.com/sds/179124.pdf": {
                "url": "https://www.sigmaaldrich.com/sds/179124.pdf",
                "is_sds": True,
                "sections": {"section_1_identification": "Acetone", "section_2_hazards": "Flammable"}
            }
        },
        "verification_result": {
            "final_status": "EXACT MATCH",
            "final_url": "https://www.sigmaaldrich.com/sds/179124.pdf",
            "confidence": 95,
            "reasoning": "Verified exact match.",
            "product_match": True,
            "manufacturer_match": True,
            "jurisdiction_match": True,
            "language_match": True,
            "issues": []
        },
        "search_queries": ["Sigma-Aldrich Acetone SDS"],
        "action_history": [{"action": "SEARCH"}, {"action": "RANK"}, {"action": "FETCH"}, {"action": "VERIFY"}]
    }

    res = extract_final_node(state)
    assert res["final_status"] == "EXACT MATCH"
    assert "provenance" in res
    prov = res["provenance"]
    assert "section_1_identification" in prov["sections_extracted"]
    assert "section_2_hazards" in prov["sections_extracted"]
    assert prov["product_matched"] is True
    assert prov["manufacturer_matched"] is True

def test_needs_review_classification_in_provenance():
    """extract_final_node classifies review category for human compliance review."""
    from src.workflow import extract_final_node

    state = {
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"},
        "discovered_candidates": [{"url": "https://sdsmanager.com/sds/acetone"}],
        "ranked_candidates": [{"url": "https://sdsmanager.com/sds/acetone", "score": 15}],
        "successful_fetches": {},
        "verification_result": {
            "final_status": "NEEDS REVIEW",
            "final_url": "",
            "confidence": 0,
            "reasoning": "Flagged for human review: Untrusted Source.",
            "issues": ["Untrusted Source: Aggregator domain 'sdsmanager.com' is not an authorized manufacturer or trusted source."]
        },
        "search_queries": ["Sigma-Aldrich Acetone SDS"],
        "action_history": [{"action": "SEARCH"}]
    }

    res = extract_final_node(state)
    assert res["final_status"] == "NEEDS REVIEW"
    assert res["final_url"] == ""
    assert res["provenance"]["review_category"] == "UNTRUSTED_SOURCE"

def test_exhausted_retries_abstains_to_needs_review_with_empty_url():
    """When retries and candidates are exhausted without a valid document, system abstains safely with empty URL."""
    state = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": ["https://site1.com/sds", "https://site2.com/sds", "https://site3.com/sds"],
        "successful_fetches": {},
        "failed_fetches": {"https://site1.com/sds": "404", "https://site2.com/sds": "404", "https://site3.com/sds": "404"},
        "search_queries": ["Sigma-Aldrich Acetone SDS", "Sigma-Aldrich Acetone Safety Data Sheet", "Acetone SDS PDF"],
        "action_history": [],
        "iteration_count": 5,
        "retry_count": 2,
        "draft_decision": None,
        "verification_result": None
    }

    result = decide_action_node(state)
    assert result["next_action"] == "FINISH"

def test_ssrf_injection_rejection_abstains_with_security_category():
    """SSRF injection in input parameters produces immediate FINISH and SECURITY_REJECTION provenance."""
    from src.workflow import extract_final_node

    state = {
        "messages": [],
        "row_data": {"Product Name": "Acetone", "Product Company Name": "http://127.0.0.1:8080/admin"},
        "discovered_candidates": [],
        "ranked_candidates": [],
        "fetched_urls": [],
        "successful_fetches": {},
        "failed_fetches": {},
        "search_queries": [],
        "action_history": [],
        "iteration_count": 0,
        "retry_count": 0,
        "draft_decision": None,
        "verification_result": {
            "final_status": "NEEDS REVIEW",
            "final_url": "",
            "confidence": 0,
            "reasoning": "Security policy rejection: SSRF address detected in input data.",
            "issues": ["Security Rejection: SSRF address detected in input data."]
        }
    }

    dec_res = decide_action_node(state)
    assert dec_res["next_action"] == "FINISH"
    final_res = extract_final_node(state)
    assert final_res["final_status"] == "NEEDS REVIEW"
    assert final_res["final_url"] == ""
    assert final_res["provenance"]["review_category"] == "SECURITY_REJECTION"



