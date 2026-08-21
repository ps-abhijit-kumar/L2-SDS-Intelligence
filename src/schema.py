from pydantic import BaseModel, Field

class SDSValidationResult(BaseModel):
    status: str = Field(
        description="Must be exactly one of 'EXACT MATCH', 'BEST AVAILABLE', or 'NEEDS REVIEW'."
    )
    confidence: int = Field(
        description="An integer from 0 to 100 representing confidence in this document."
    )
    detailed_reasoning: str = Field(
        description="A 1-2 sentence explanation citing evidence from the document (product, company, jurisdiction, language) justifying the status."
    )
    final_url: str = Field(
        description="The final URL of the validated document. Empty string if no valid candidate found."
    )
