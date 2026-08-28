import pytest
from pydantic import ValidationError
from src.schema import SDSValidationResult, VerificationResult, ActionDecision, SDSEvidence, is_valid_http_url

def test_sds_validation_result_valid():
    res = SDSValidationResult(
        status="EXACT MATCH",
        confidence=95,
        detailed_reasoning="Verified authentic SDS for Acetone from Sigma-Aldrich.",
        final_url="https://www.sigmaaldrich.com/US/en/sds/sial/179124"
    )
    assert res.status == "EXACT MATCH"
    assert res.confidence == 95
    assert res.final_url.startswith("https://")

def test_sds_validation_result_best_available_valid():
    res = SDSValidationResult(
        status="BEST AVAILABLE",
        confidence=75,
        detailed_reasoning="Best available SDS retrieved matching chemical profile.",
        final_url="https://www.sigmaaldrich.com/sds/landing/179124"
    )
    assert res.status == "BEST AVAILABLE"
    assert res.confidence == 75
    assert res.final_url.startswith("https://")

def test_sds_validation_result_best_available_requires_url():
    # Enforces Phase 6: BEST AVAILABLE cannot have empty final_url
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="BEST AVAILABLE",
            confidence=70,
            detailed_reasoning="Best available match but without URL.",
            final_url=""
        )

def test_sds_validation_result_reject_invalid_status():
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="NOT REAL",
            confidence=90,
            detailed_reasoning="Some reasoning here.",
            final_url="https://example.com/sds.pdf"
        )

def test_sds_validation_result_reject_negative_confidence():
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="NEEDS REVIEW",
            confidence=-5,
            detailed_reasoning="Negative confidence is invalid.",
            final_url=""
        )

def test_sds_validation_result_reject_over_100_confidence():
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="EXACT MATCH",
            confidence=999,
            detailed_reasoning="Excessive confidence is invalid.",
            final_url="https://www.fishersci.com/sds.pdf"
        )

def test_sds_validation_result_reject_invalid_url():
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="EXACT MATCH",
            confidence=90,
            detailed_reasoning="Valid reasoning text.",
            final_url="not-a-valid-url"
        )

def test_sds_validation_result_reject_empty_reasoning():
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="NEEDS REVIEW",
            confidence=0,
            detailed_reasoning="   ",
            final_url=""
        )

def test_sds_validation_result_exact_match_requires_url():
    with pytest.raises(ValidationError):
        SDSValidationResult(
            status="EXACT MATCH",
            confidence=90,
            detailed_reasoning="Cannot have exact match without URL.",
            final_url=""
        )

def test_verification_result_valid():
    ver = VerificationResult(
        approved=True,
        issues=[],
        corrections={},
        evidence_sufficient=True,
        final_status="EXACT MATCH",
        final_url="https://www.fishersci.com/sds/123.pdf",
        confidence=90,
        reasoning="Full match for product and manufacturer.",
        product_match=True,
        manufacturer_match=True
    )
    assert ver.approved is True
    assert ver.confidence == 90

def test_url_safety_validator_function():
    assert is_valid_http_url("https://www.fishersci.com/sds.pdf") is True
    assert is_valid_http_url("http://sigmaaldrich.com/doc") is True
    assert is_valid_http_url("file:///etc/passwd") is False
    assert is_valid_http_url("ftp://server.com") is False
    assert is_valid_http_url("http://localhost:8000") is False
    assert is_valid_http_url("http://127.0.0.1/doc") is False
    assert is_valid_http_url("http://example.com/sds.pdf") is False
