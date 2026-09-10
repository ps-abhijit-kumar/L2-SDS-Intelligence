import pytest
from src.agent.workflow import perform_verification

def test_reflection_approves_perfect_match():
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Sigma-Aldrich",
        "Part Number": "179124",
        "Country": "United States"
    }
    target_url = "https://www.sigmaaldrich.com/sds/179124.pdf"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "language": "English",
            "country": "United States",
            "part_numbers": ["179124"],
            "cas_numbers": ["67-64-1"],
            "raw_snippet": "Sigma-Aldrich Safety Data Sheet for Acetone product 179124. CAS 67-64-1.",
            "sections": {"section_1_identification": "Product Name: Acetone, Manufacturer: Sigma-Aldrich"}
        }
    }

    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=95,
        draft_reasoning="Verified Acetone match.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )

    assert ver.approved is True
    assert ver.final_status == "EXACT MATCH"
    assert ver.confidence == 95
    assert ver.product_match is True
    assert ver.manufacturer_match is True
    assert ver.part_number_match is True

def test_reflection_downgrades_manufacturer_mismatch():
    row_data = {
        "Product Name": "Acetone",
        "Product Company Name": "Fisher Scientific",  # Request is for Fisher
        "Country": "United States"
    }
    target_url = "https://www.sigmaaldrich.com/sds/acetone.pdf"  # Candidate is from Sigma
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": True,
            "language": "English",
            "country": "United States",
            "part_numbers": [],
            "cas_numbers": ["67-64-1"],
            "raw_snippet": "Sigma-Aldrich Safety Data Sheet for Acetone. CAS 67-64-1.",
            "sections": {"section_1_identification": "Product Name: Acetone, Manufacturer: Sigma-Aldrich"}
        }
    }

    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=95,
        draft_reasoning="Acetone match.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )

    # Should downgrade from EXACT MATCH to BEST AVAILABLE
    assert ver.final_status == "BEST AVAILABLE"
    assert ver.manufacturer_match is False
    assert ver.confidence <= 75
    assert any("Manufacturer Mismatch" in issue for issue in ver.issues)

def test_reflection_rejects_non_sds_document():
    row_data = {
        "Product Name": "Methanol",
        "Product Company Name": "Thermo Fisher"
    }
    target_url = "https://www.thermofisher.com/products/methanol.html"
    discovered = [{"url": target_url}]
    successful = {
        target_url: {
            "url": target_url,
            "is_sds": False,  # Commercial product page, not SDS
            "raw_snippet": "Buy Methanol online. High purity solvents for HPLC.",
            "sections": {}
        }
    }

    ver = perform_verification(
        row_data=row_data,
        draft_status="EXACT MATCH",
        draft_url=target_url,
        draft_confidence=80,
        draft_reasoning="Product page found.",
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches={}
    )

    assert ver.final_status == "NEEDS REVIEW"
    assert any("Document Authenticity" in issue for issue in ver.issues)
