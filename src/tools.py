import re
import time
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from ddgs import DDGS

from src.security import safe_fetch_document, SecurityError
from src.sds_parser import parse_sds_document, normalize_identifier, normalize_text
from src.schema import SDSEvidence

TRUSTED_SITES = [
    "sigmaaldrich.com",
    "fishersci.com",
    "thermofisher.com",
    "vwr.com",
    "avantorsciences.com",
    "merckmillipore.com",
    "tcichemicals.com",
    "spectrumchemical.com",
    "scbt.com",
    "caymanchem.com",
    "bio-rad.com",
    "promega.com",
    "neb.com",
    "abcam.com",
    "cellsignal.com",
    "3m.com",
    "ecolab.com",
    "dow.com",
    "basf.com",
    "dupont.com",
    "eastman.com",
    "evonik.com",
    "honeywell.com",
    "airgas.com",
    "linde.com",
    "mathesongas.com",
    "cdc.gov/niosh",
    "echa.europa.eu",
    "pubchem.ncbi.nlm.nih.gov",
    "ilpi.com",
    "msdssolutions.com",
]

@tool
def search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """
    Executes a targeted web search using DuckDuckGo to discover candidate Safety Data Sheets.
    Returns a deduplicated list of search results containing url, snippet, and title.
    """
    results = []
    unique_urls = set()

    try:
        with DDGS() as ddgs:
            search_res = ddgs.text(query, max_results=max_results)
            if search_res:
                for res in search_res:
                    url = res.get("href", "")
                    if url and url not in unique_urls:
                        unique_urls.add(url)
                        results.append({
                            "url": url,
                            "title": res.get("title", ""),
                            "snippet": res.get("body", "")
                        })
            time.sleep(0.3)
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]

    return results

@tool
def rank_sds_candidates(
    candidates: list[dict],
    target_product: str,
    target_company: str,
    target_part_number: str = "",
    target_country: str = ""
) -> list[dict]:
    """
    Deterministically scores and ranks candidate SDS URLs based on multi-factor heuristics.
    Factors: Product name match, company/manufacturer match, part number match, trusted domain bonus,
    and PDF filetype preference. Returns candidates sorted in descending order of utility score (0-100).
    """
    prod_norm = normalize_text(target_product)
    comp_norm = normalize_text(target_company)
    part_norm = normalize_identifier(target_part_number)
    country_norm = normalize_text(target_country)

    ranked = []
    for cand in candidates:
        if not isinstance(cand, dict) or "error" in cand or not cand.get("url"):
            continue

        url = str(cand.get("url", "")).lower()
        title = str(cand.get("title", "")).lower()
        snippet = str(cand.get("snippet", "")).lower()
        combined_text = f"{title} {snippet}"

        score = 0

        if prod_norm:
            if prod_norm in url:
                score += 35
            elif prod_norm in combined_text:
                score += 25
            else:
                prod_tokens = prod_norm.split()
                if prod_tokens:
                    token_matches = sum(1 for tok in prod_tokens if tok in combined_text or tok in url)
                    score += int(20 * (token_matches / len(prod_tokens)))

        if comp_norm:
            comp_clean = re.sub(r'[^a-z0-9]', '', comp_norm)
            if comp_clean and comp_clean in url:
                score += 25
            elif comp_norm in combined_text:
                score += 15
            else:
                comp_tokens = comp_norm.split()
                if comp_tokens:
                    token_matches = sum(1 for tok in comp_tokens if tok in combined_text or tok in url)
                    score += int(10 * (token_matches / len(comp_tokens)))

        if ".pdf" in url:
            score += 20
        elif "sds" in url or "msds" in url or "safety-data-sheet" in url:
            score += 10

        if any(ts in url for ts in TRUSTED_SITES):
            score += 10

        final_score = max(0, min(100, score))

        ranked.append({
            "url": cand["url"],
            "score": final_score,
            "title": cand.get("title", ""),
            "snippet": cand.get("snippet", "")
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)

@tool
def fetch_document_text(url: str) -> str:
    """
    Safely downloads and extracts structured Safety Data Sheet text from a URL (PDF or HTML).
    Includes full SSRF protection, redirect verification, stream bounds, and section extraction.
    Returns structured evidence summary containing product, manufacturer, sections, and CAS numbers.
    """
    try:
        data, content_type, final_url = safe_fetch_document(url, timeout=10.0)
        evidence = parse_sds_document(data, content_type, final_url)

        if not evidence.fetched_successfully:
            return f"Error fetching/parsing document: {evidence.error or 'Unknown parsing error'}"

        summary_lines = [
            f"--- SDS Document Evidence from: {final_url} ---",
            f"Is Authentic SDS: {evidence.is_sds}",
            f"Document Language: {evidence.language}",
            f"Jurisdiction/Region: {evidence.country}",
            f"Revision Date: {evidence.revision_date or 'Not specified'}",
            f"CAS Numbers Found: {', '.join(evidence.cas_numbers) if evidence.cas_numbers else 'None'}",
            f"Part Numbers Found: {', '.join(evidence.part_numbers) if evidence.part_numbers else 'None'}",
        ]

        if evidence.sections:
            summary_lines.append("\nKey Extracted Sections:")
            for sec_name, sec_text in evidence.sections.items():
                summary_lines.append(f"[{sec_name}]:\n{sec_text[:400]}")
        else:
            summary_lines.append(f"\nDocument Snippet:\n{evidence.raw_snippet[:800]}")

        return "\n".join(summary_lines)

    except SecurityError as sec_err:
        return f"Security Error: SSRF / network policy violation: {str(sec_err)}"
    except Exception as e:
        return f"Error fetching document: {str(e)}"
