import pytest
from src.tools import search_duckduckgo, rank_sds_candidates, fetch_document_text

def test_search_duckduckgo():
    # Test that search returns a list of dictionaries with expected keys
    # or an error dictionary.
    results = search_duckduckgo.invoke({"query": "Acetone SDS", "max_results": 1})
    assert isinstance(results, list)
    if results and "error" not in results[0]:
        assert "url" in results[0]
        assert "snippet" in results[0]

def test_rank_sds_candidates():
    # Deterministic test
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

def test_fetch_document_error_handling():
    # Should handle bad urls safely
    res = fetch_document_text.invoke({"url": "http://this-does-not-exist.local"})
    assert "Error" in res
