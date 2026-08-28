import pytest
from src.tools import (
    search_duckduckgo,
    rank_sds_candidates,
    fetch_document_text,
    score_document_evidence,
    generate_retrieval_queries
)
from src.schema import SDSEvidence

def test_search_duckduckgo():
    results = search_duckduckgo.invoke({"query": "Acetone SDS", "max_results": 1})
    assert isinstance(results, list)
    if results and "error" not in results[0]:
        assert "url" in results[0]
        assert "snippet" in results[0]

def test_rank_sds_candidates():
    candidates = [
        {"url": "http://randomsite.com/doc", "snippet": "some text"},
        {"url": "http://sigmaaldrich.com/acetone.pdf", "snippet": "Safety Data Sheet for Acetone"}
    ]
    ranked = rank_sds_candidates.invoke({
        "candidates": candidates,
        "target_product": "Acetone",
        "target_company": "Sigma-Aldrich"
    })

    assert len(ranked) == 2
    assert ranked[0]["url"] == "http://sigmaaldrich.com/acetone.pdf"
    assert ranked[0]["score"] > ranked[1]["score"]
    assert "sub_scores" in ranked[0]
    assert ranked[0]["sub_scores"]["product_score"] > 0
    assert ranked[0]["sub_scores"]["manufacturer_score"] > 0

def test_rank_sds_candidates_competing_manufacturer_rejection():
    # Fisher Scientific request vs Sigma competitor link and Fisher official link
    candidates = [
        {"url": "https://www.sigmaaldrich.com/US/en/sds/acetone.pdf", "title": "Acetone SDS", "snippet": "Sigma-Aldrich Acetone"},
        {"url": "https://www.fishersci.com/store/msds?partNumber=A4164", "title": "Acetone SDS", "snippet": "Fisher Chemical Acetone Safety Data Sheet"}
    ]
    ranked = rank_sds_candidates.invoke({
        "candidates": candidates,
        "target_product": "Acetone",
        "target_company": "Fisher Scientific"
    })

    # Fisher Scientific link should rank higher than competing Sigma link for a Fisher request
    assert ranked[0]["url"] == "https://www.fishersci.com/store/msds?partNumber=A4164"
    assert ranked[0]["sub_scores"]["manufacturer_score"] > ranked[1]["sub_scores"]["manufacturer_score"]

def test_rank_sds_candidates_aggregator_demotion():
    candidates = [
        {"url": "https://www.chemicalbook.com/ProductMSDSDetail_123.htm", "title": "Hydrochloric Acid SDS", "snippet": "Spectrum Chemical Hydrochloric Acid 37%"},
        {"url": "https://www.spectrumchemical.com/chemical/h1035.pdf", "title": "Hydrochloric Acid 37% Safety Data Sheet", "snippet": "Spectrum Chemical"}
    ]
    ranked = rank_sds_candidates.invoke({
        "candidates": candidates,
        "target_product": "Hydrochloric Acid 37%",
        "target_company": "Spectrum Chemical"
    })
    assert ranked[0]["url"] == "https://www.spectrumchemical.com/chemical/h1035.pdf"
    assert ranked[1]["sub_scores"]["aggregator_penalty"] < 0

def test_rank_sds_candidates_cas_and_part_scoring():
    candidates = [
        {"url": "https://www.sigmaaldrich.com/sds/179124.pdf", "title": "Acetone CAS 67-64-1 Part 179124", "snippet": "Sigma SDS"}
    ]
    ranked = rank_sds_candidates.invoke({
        "candidates": candidates,
        "target_product": "Acetone",
        "target_company": "Sigma-Aldrich",
        "target_part_number": "179124",
        "target_cas": "67-64-1"
    })
    assert len(ranked) == 1
    assert ranked[0]["sub_scores"]["part_cas_score"] == 15

def test_stage_b_document_evidence_scoring_section1_and_cas():
    """Verify Stage B document evidence scoring awards full points for Section 1 + CAS."""
    ev = SDSEvidence(
        url="https://www.sigmaaldrich.com/sds/acetone.pdf",
        is_sds=True,
        product_name="Acetone",
        manufacturer="Sigma-Aldrich Inc.",
        cas_numbers=["67-64-1"],
        part_numbers=["179124"],
        country="United States",
        language="English",
        sections={
            "section_1_identification": "Product Name: Acetone, Manufacturer: Sigma-Aldrich",
            "section_3_composition": "Substance: Acetone, CAS-No: 67-64-1"
        },
        url_type="pdf",
        raw_snippet="Safety Data Sheet for Acetone from Sigma-Aldrich.",
        fetched_successfully=True
    )
    score, breakdown, reasons = score_document_evidence(
        evidence=ev,
        target_product="Acetone",
        target_company="Sigma-Aldrich",
        target_part_number="179124",
        target_cas="67-64-1",
        target_country="United States",
        target_language="English"
    )
    assert score >= 90
    assert breakdown["structure_score"] == 25
    assert breakdown["product_evidence_score"] == 35
    assert breakdown["manufacturer_evidence_score"] == 30
    assert breakdown["cas_part_score"] == 15

def test_generate_retrieval_queries():
    queries = generate_retrieval_queries(
        product="Acetone",
        company="Sigma-Aldrich",
        part_number="179124",
        cas="67-64-1"
    )
    assert len(queries) >= 3
    assert any("Sigma-Aldrich Acetone SDS" in q for q in queries)
    assert any("67-64-1" in q for q in queries)

def test_fetch_document_error_handling():
    res = fetch_document_text.invoke({"url": "http://this-does-not-exist.local"})
    assert "Error" in res or "Security Error" in res
