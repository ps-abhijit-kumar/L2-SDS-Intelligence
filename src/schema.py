import re
from typing import Optional, Dict, Any, List, Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, model_validator

ValidStatus = Literal["EXACT MATCH", "BEST AVAILABLE", "NEEDS REVIEW"]
ActionType = Literal["SEARCH", "RANK", "FETCH", "VERIFY", "FINISH", "RETRY"]

BLOCKED_DOMAINS = {"example.com", "example.org", "wikipedia.org", "localhost", "127.0.0.1"}

def is_valid_http_url(url: str) -> bool:
    """Validates that a URL is a valid absolute HTTP or HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        host = parsed.netloc.split(":")[0].lower()
        if host in BLOCKED_DOMAINS or host.endswith(".local") or host.endswith(".internal"):
            return False
        return True
    except Exception:
        return False

class NormalizedSDSRequest(BaseModel):
    """Normalized four-field chemical Safety Data Sheet request extracted semantically from Excel."""
    s_no: int = Field(default=1, description="Sequential request index.")
    product_name: str = Field(..., description="Chemical substance or product trade name.")
    manufacturer: str = Field(..., description="Chemical manufacturer, supplier, or product company.")
    language: str = Field(..., description="Requested SDS document language.")
    country: str = Field(..., description="Target jurisdiction or destination country.")
    part_number: Optional[str] = Field(default="", description="Optional part number, catalog code, or CAS number.")
    status: str = Field(default="PENDING", description="Verification verdict status.")
    confidence: int = Field(default=0, ge=0, le=100, description="Verification confidence integer (0-100).")
    found_url: str = Field(default="", description="Grounded SDS document URL or landing page.")
    url_type: Optional[Literal["pdf", "landing_page"]] = Field(default="pdf", description="Type of retrieved URL.")
    detailed_reasoning: str = Field(default="", description="Evaluation reasoning.")
    source_sheet: Optional[str] = Field(default=None, description="Origin worksheet in source workbook.")
    source_row: Optional[int] = Field(default=None, description="Origin physical row number in worksheet.")

    @field_validator("product_name", "manufacturer", "language", "country")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Required SDS search identity field must not be empty.")
        return v.strip()

class SDSEvidence(BaseModel):
    """Structured extraction of evidence from a fetched SDS candidate."""
    url: str
    product_name: str = ""
    manufacturer: str = ""
    part_numbers: List[str] = Field(default_factory=list)
    cas_numbers: List[str] = Field(default_factory=list)
    revision_date: str = ""
    document_date: str = ""
    language: str = ""
    country: str = ""
    is_sds: bool = False
    sections: Dict[str, str] = Field(default_factory=dict)
    url_type: Literal["pdf", "landing_page"] = "pdf"
    raw_snippet: str = ""
    error: Optional[str] = None
    fetched_successfully: bool = True

class ActionDecision(BaseModel):
    """Dynamic action selected by the agent based on state and prerequisites."""
    action: ActionType = Field(
        description="The next discrete action: SEARCH, RANK, FETCH, VERIFY, FINISH, or RETRY."
    )
    reason: str = Field(
        description="Detailed explanation justifying why this action was selected given the current state."
    )
    target_url: Optional[str] = Field(
        default=None,
        description="Target URL if action is FETCH or candidate-targeted RETRY."
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Model-selected targeted query string if action is SEARCH or query-adaptive RETRY."
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries attempted so far."
    )

class VerificationResult(BaseModel):
    """Structured output from the independent reflection/verification stage."""
    approved: bool = Field(
        description="True if the draft decision is completely supported by grounded evidence."
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of identified discrepancies, missing fields, or grounding issues."
    )
    corrections: Dict[str, Any] = Field(
        default_factory=dict,
        description="Field corrections if status, url, or confidence must be revised."
    )
    evidence_sufficient: bool = Field(
        default=True,
        description="Whether the gathered document evidence is sufficient to make a final determination."
    )
    final_status: ValidStatus = Field(
        description="Grounded status after verification ('EXACT MATCH', 'BEST AVAILABLE', 'NEEDS REVIEW')."
    )
    final_url: str = Field(
        default="",
        description="Verified grounded URL, or empty string if no valid candidate exists."
    )
    url_type: Optional[Literal["pdf", "landing_page"]] = Field(
        default="pdf",
        description="Whether the validated URL is a direct PDF or an SDS landing/download page."
    )
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Grounded confidence integer bounded strictly between 0 and 100."
    )
    reasoning: str = Field(
        ...,
        min_length=5,
        max_length=2500,
        description="Detailed reflection explaining evidence justification, field matches, or downgrade reasons."
    )
    product_match: bool = Field(
        default=False,
        description="Whether the product name in evidence matches the request."
    )
    manufacturer_match: bool = Field(
        default=False,
        description="Whether the manufacturer in evidence matches the request."
    )
    part_number_match: Optional[bool] = Field(
        default=None,
        description="Whether part number matches if present in request."
    )
    jurisdiction_match: Optional[bool] = Field(
        default=None,
        description="Whether jurisdiction/language matches request."
    )
    required_additional_evidence: List[str] = Field(
        default_factory=list,
        description="Specific missing fields if evidence is insufficient (e.g. ['section_1_identification'])."
    )

    @field_validator("final_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            return ""
        v_clean = v.strip()
        if not is_valid_http_url(v_clean):
            raise ValueError(f"Invalid URL provided: '{v}'. Must be a valid HTTP/HTTPS URL.")
        return v_clean

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("Reasoning must contain at least 5 non-whitespace characters.")
        return v.strip()

class SDSValidationResult(BaseModel):
    """Strict structured final output schema for chemical Safety Data Sheet retrieval."""
    status: ValidStatus = Field(
        description="Must be exactly one of 'EXACT MATCH', 'BEST AVAILABLE', or 'NEEDS REVIEW'."
    )
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="An integer from 0 to 100 representing grounded confidence in this document."
    )
    detailed_reasoning: str = Field(
        ...,
        min_length=5,
        max_length=2500,
        description="A clear 1-3 sentence explanation citing evidence from the document (product, company, jurisdiction, language) justifying the status."
    )
    final_url: str = Field(
        default="",
        description="The final URL of the validated document. Must be non-empty for EXACT MATCH and BEST AVAILABLE, and empty for ungrounded NEEDS REVIEW."
    )
    url_type: Optional[Literal["pdf", "landing_page"]] = Field(
        default="pdf",
        description="Whether the final URL points directly to an SDS PDF or an SDS landing/download page."
    )
    provenance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Grounding metadata proving discovered_at, source_query, and fetch success."
    )

    @field_validator("final_url")
    @classmethod
    def validate_final_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            return ""
        v_clean = v.strip()
        if not is_valid_http_url(v_clean):
            raise ValueError(f"Invalid URL: '{v}'. Must be a valid absolute HTTP or HTTPS URL.")
        return v_clean

    @field_validator("detailed_reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("detailed_reasoning must be at least 5 characters long and non-empty.")
        return v.strip()

    @model_validator(mode="after")
    def validate_status_and_url_consistency(self):
        # Both EXACT MATCH and BEST AVAILABLE require a grounded, non-empty final URL
        if self.status in ["EXACT MATCH", "BEST AVAILABLE"]:
            if not self.final_url or not str(self.final_url).strip():
                raise ValueError(f"'{self.status}' status requires a valid non-empty grounded final_url.")
            if self.status == "EXACT MATCH" and self.confidence < 50:
                raise ValueError("EXACT MATCH status requires confidence >= 50.")
            if self.status == "BEST AVAILABLE" and self.confidence < 30:
                raise ValueError("BEST AVAILABLE status requires confidence >= 30.")
        return self
