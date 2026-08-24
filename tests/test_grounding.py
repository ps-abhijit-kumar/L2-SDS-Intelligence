import pytest
from src.workflow import perform_verification

def test_grounding_invariant_reject_unsearched_url():
    # Final URL is NOT in discovered candidates
    row_data = {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"}
    discovered = [{"url": "https://www.sigmaaldrich.com/sds/acetone.pdf"}]
    successful = {"https://www.hallucinated-site.com/sds.pdf": {"url": "https://www.hallucinated-site.com/sds.pdf", "is_sds": True, "raw_snippet": "Acetone SDS", "sections": {}}}

    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url="https://www.hallucinated-site.com/sds.pdf",
        draft_confidence=95,
        draft_reasoning="Hallucinated candidate",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )

    assert ver.approved is False
    assert ver.final_status == "NEEDS REVIEW"
    assert any("Grounding Failure" in issue for issue in ver.issues)

def test_grounding_invariant_reject_unfetched_url():
    # URL in discovered candidates but never successfully fetched
    row_data = {"Product Name": "Acetone", "Product Company Name": "Sigma-Aldrich"}
    discovered = [{"url": "https://www.sigmaaldrich.com/sds/acetone.pdf"}]
    successful = {}  # Empty fetched evidence

    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url="https://www.sigmaaldrich.com/sds/acetone.pdf",
        draft_confidence=90,
        draft_reasoning="Valid candidate",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )

    assert ver.approved is False
    assert ver.final_status == "NEEDS REVIEW"
    assert any("Grounding Failure" in issue for issue in ver.issues)
