import pytest
from src.agent.evaluation import (
    evaluate_status,
    evaluate_url_grounding,
    evaluate_product,
    evaluate_manufacturer,
    evaluate_country,
    evaluate_language
)

def test_a_exact_match_vs_best_available_no_credit():
    """TEST A: Expected EXACT MATCH, Actual BEST AVAILABLE -> status must NOT receive credit."""
    assert evaluate_status("EXACT MATCH", "BEST AVAILABLE") is False

def test_b_best_available_vs_needs_review_mismatch():
    """TEST B: Expected BEST AVAILABLE, Actual NEEDS REVIEW -> must be reported as status mismatch."""
    assert evaluate_status("BEST AVAILABLE", "NEEDS REVIEW") is False

def test_c_independent_manufacturer_rejection_despite_internal_claim():
    """TEST C: Expected manufacturer 'ABC', Actual 'XYZ' -> evaluator must mark manufacturer incorrect regardless of internal claims."""
    fetched_evidence = {
        "url": "https://xyz-chemicals.com/doc.pdf",
        "product_name": "Acetone",
        "manufacturer": "XYZ Chemicals Inc",
        "raw_snippet": "Acetone manufactured by XYZ Chemicals Inc.",
        "sections": {}
    }
    # Evaluator compares independently against expected 'ABC Chemical Corp'
    res = evaluate_manufacturer(
        expected_manufacturer="ABC Chemical Corp",
        expected_status="EXACT MATCH",
        actual_status="EXACT MATCH",
        fetched_evidence=fetched_evidence,
        actual_url="https://xyz-chemicals.com/doc.pdf"
    )
    assert res is False

def test_d_url_grounding_rejects_unapproved_domain():
    """TEST D: Expected URL domain = manufacturer.com, Actual URL = random-site.com -> URL grounding must be False."""
    acceptable_domains = ["sigmaaldrich.com", "merckmillipore.com"]
    acceptable_urls = []
    
    # Even if URL contains keyword 'sds' or 'sigma', unapproved domain must be rejected
    res = evaluate_url_grounding(
        expected_status="EXACT MATCH",
        actual_status="EXACT MATCH",
        actual_url="https://random-site.com/sds/sigma_acetone.pdf",
        acceptable_domains=acceptable_domains,
        acceptable_urls=acceptable_urls
    )
    assert res is False

def test_e_needs_review_expected_and_actual():
    """TEST E: Expected NEEDS REVIEW, Actual NEEDS REVIEW -> status correct and empty URL is grounded."""
    assert evaluate_status("NEEDS REVIEW", "NEEDS REVIEW") is True
    
    # URL grounding for NEEDS REVIEW expects empty string
    url_res = evaluate_url_grounding(
        expected_status="NEEDS REVIEW",
        actual_status="NEEDS REVIEW",
        actual_url="",
        acceptable_domains=[],
        acceptable_urls=[]
    )
    assert url_res is True

def test_f_exact_match_with_wrong_manufacturer_fails_overall():
    """TEST F: Expected EXACT MATCH, Actual EXACT MATCH with wrong manufacturer -> manufacturer fails and overall must fail."""
    fetched_evidence = {
        "url": "https://sigmaaldrich.com/doc.pdf",
        "product_name": "Acetone",
        "manufacturer": "Sigma-Aldrich",
        "raw_snippet": "Sigma-Aldrich Acetone SDS.",
        "sections": {}
    }
    status_correct = evaluate_status("EXACT MATCH", "EXACT MATCH")
    url_grounded = evaluate_url_grounding(
        "EXACT MATCH", "EXACT MATCH", "https://sigmaaldrich.com/doc.pdf", ["sigmaaldrich.com"], []
    )
    product_correct = evaluate_product("Acetone", "EXACT MATCH", "EXACT MATCH", fetched_evidence, "https://sigmaaldrich.com/doc.pdf")
    # Expected manufacturer was Fisher Scientific
    mfg_correct = evaluate_manufacturer("Fisher Scientific", "EXACT MATCH", "EXACT MATCH", fetched_evidence, "https://sigmaaldrich.com/doc.pdf")
    country_correct = evaluate_country("United States", "EXACT MATCH", "EXACT MATCH", fetched_evidence)
    lang_correct = evaluate_language("English", "EXACT MATCH", "EXACT MATCH", fetched_evidence)

    assert status_correct is True
    assert url_grounded is True
    assert product_correct is True
    assert mfg_correct is False

    overall_correct = (status_correct and url_grounded and product_correct and mfg_correct and country_correct and lang_correct)
    assert overall_correct is False

def test_g_exact_match_all_correct_passes_overall():
    """TEST G: Expected EXACT MATCH, Actual EXACT MATCH with all fields matching and acceptable URL -> passes overall."""
    fetched_evidence = {
        "url": "https://sigmaaldrich.com/sds/acetone.pdf",
        "product_name": "Acetone",
        "manufacturer": "Sigma-Aldrich",
        "country": "United States",
        "language": "English",
        "raw_snippet": "Sigma-Aldrich Safety Data Sheet for Acetone. United States OSHA compliant.",
        "sections": {}
    }
    status_correct = evaluate_status("EXACT MATCH", "EXACT MATCH")
    url_grounded = evaluate_url_grounding("EXACT MATCH", "EXACT MATCH", "https://sigmaaldrich.com/sds/acetone.pdf", ["sigmaaldrich.com"], [])
    product_correct = evaluate_product("Acetone", "EXACT MATCH", "EXACT MATCH", fetched_evidence, "https://sigmaaldrich.com/sds/acetone.pdf")
    mfg_correct = evaluate_manufacturer("Sigma-Aldrich", "EXACT MATCH", "EXACT MATCH", fetched_evidence, "https://sigmaaldrich.com/sds/acetone.pdf")
    country_correct = evaluate_country("United States", "EXACT MATCH", "EXACT MATCH", fetched_evidence)
    lang_correct = evaluate_language("English", "EXACT MATCH", "EXACT MATCH", fetched_evidence)

    overall_correct = (status_correct and url_grounded and product_correct and mfg_correct and country_correct and lang_correct)
    assert overall_correct is True

def test_h_needs_review_with_spurious_url_fails_grounding():
    """TEST H: Expected NEEDS REVIEW, but Actual output returned a URL -> URL grounding must fail."""
    url_res = evaluate_url_grounding(
        expected_status="NEEDS REVIEW",
        actual_status="NEEDS REVIEW",
        actual_url="https://random-site.com/sds.pdf",
        acceptable_domains=[],
        acceptable_urls=[]
    )
    assert url_res is False
