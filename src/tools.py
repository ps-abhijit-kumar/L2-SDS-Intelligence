import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional, Set, Tuple
from langchain_core.tools import tool
from ddgs import DDGS

from src.security import safe_fetch_document, SecurityError, is_valid_url_syntax
from src.sds_parser import (
    parse_sds_document,
    normalize_identifier,
    normalize_text,
    normalize_url,
    is_chemical_name_match,
    extract_base_chemical_tokens
)
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
    "lab-honeywell.com",
    "airgas.com",
    "linde.com",
    "mathesongas.com",
    "cdc.gov/niosh",
    "echa.europa.eu",
    "ilpi.com",
    "msdssolutions.com",
]

AGGREGATOR_DOMAINS = [
    "chemicalbook.com",
    "guidechem.com",
    "chemblink.com",
    "sciencedirect.com",
    "lookchem.com",
    "chemspider.com",
    "chemnet.com",
    "wikipedia.org",
    "pubchem.ncbi.nlm.nih.gov",
    "cdhfinechemical.com",
    "sdsinventory.com",
    "hazcoms.com",
    "msdsdigital.com",
    "sdsmanager.com",
    "sds-manager.com",
    "labchem.com",
    "alfa-chem.com"
]

MANUFACTURER_DOMAINS: Dict[str, List[str]] = {
    "sigma aldrich": ["sigmaaldrich.com", "merckmillipore.com", "milliporesigma.com", "emdmillipore.com"],
    "sigma": ["sigmaaldrich.com", "merckmillipore.com", "milliporesigma.com"],
    "aldrich": ["sigmaaldrich.com", "merckmillipore.com"],
    "merck": ["merckmillipore.com", "sigmaaldrich.com", "merckgroup.com", "emdmillipore.com"],
    "fisher scientific": ["fishersci.com", "thermofisher.com"],
    "fisher": ["fishersci.com", "thermofisher.com"],
    "thermo fisher": ["thermofisher.com", "fishersci.com", "alfa.com", "acros.com"],
    "thermo": ["thermofisher.com", "fishersci.com"],
    "honeywell": ["honeywell.com", "lab-honeywell.com"],
    "spectrum chemical": ["spectrumchemical.com", "fishersci.com", "sigmaaldrich.com"],
    "spectrum": ["spectrumchemical.com", "fishersci.com"],
    "avantor": ["avantorsciences.com", "vwr.com", "sigmaaldrich.com"],
    "vwr": ["vwr.com", "avantorsciences.com"],
    "tci chemicals": ["tcichemicals.com"],
    "tci": ["tcichemicals.com"],
    "santa cruz": ["scbt.com"],
    "cayman": ["caymanchem.com"],
    "bio rad": ["bio-rad.com"],
    "promega": ["promega.com"],
    "abcam": ["abcam.com"],
    "3m": ["3m.com"],
    "dow": ["dow.com"],
    "basf": ["basf.com"],
    "dupont": ["dupont.com"],
    "eastman": ["eastman.com"],
    "evonik": ["evonik.com"],
    "airgas": ["airgas.com"],
    "linde": ["linde.com"],
    "matheson": ["mathesongas.com"]
}

def get_authorized_domains_for_manufacturer(manufacturer_name: str) -> List[str]:
    """Returns official or authorized domain list for a chemical manufacturer."""
    clean_mfg = normalize_text(manufacturer_name)
    if not clean_mfg:
        return []

    domains: Set[str] = set()
    for key, doms in MANUFACTURER_DOMAINS.items():
        norm_key = normalize_text(key)
        if norm_key in clean_mfg or clean_mfg in norm_key:
            domains.update(doms)

    if not domains:
        comp_token = re.sub(r'[^a-z0-9]', '', clean_mfg)
        if comp_token and len(comp_token) > 3:
            domains.add(f"{comp_token}.com")

    return list(domains)

def generate_retrieval_queries(
    product: str,
    company: str,
    part_number: str = "",
    cas: str = "",
    country: str = "",
    language: str = "English"
) -> List[str]:
    """
    Generates a prioritized list of orthogonal search queries for chemical SDS discovery.
    """
    prod_clean = re.sub(r'["\r\n\t]', ' ', product).strip()
    comp_clean = re.sub(r'["\r\n\t]', ' ', company).strip()
    part_clean = re.sub(r'["\r\n\t]', '', part_number).strip() if part_number and not part_number.startswith("http") else ""
    cas_clean = cas.strip() if cas and re.match(r'^\d{2,7}-\d{2}-\d$', cas.strip()) else ""

    auth_domains = get_authorized_domains_for_manufacturer(company)
    queries: List[str] = []

    # Strategy 1: Targeted Official Domain Query
    if auth_domains and prod_clean:
        for dom in auth_domains[:2]:
            queries.append(f"site:{dom} {prod_clean} SDS")

    # Strategy 2: High-yield Manufacturer + Product + SDS
    if comp_clean and prod_clean:
        queries.append(f"{comp_clean} {prod_clean} SDS")

    # Strategy 3: CAS / Catalog Specific Query
    if comp_clean and prod_clean and cas_clean:
        queries.append(f"{comp_clean} {prod_clean} {cas_clean} SDS PDF")
    elif comp_clean and prod_clean and part_clean:
        queries.append(f"{comp_clean} {prod_clean} {part_clean} SDS")

    # Strategy 4: Direct PDF Search
    if prod_clean and comp_clean:
        queries.append(f"{comp_clean} {prod_clean} SDS filetype:pdf")

    return queries

@tool
def search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
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
                    if url and is_valid_url_syntax(url) and url not in unique_urls:
                        unique_urls.add(url)
                        results.append({
                            "url": url,
                            "title": str(res.get("title", "")).strip(),
                            "snippet": str(res.get("body", "")).strip(),
                            "source_query": query
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
    target_cas: str = "",
    target_country: str = "",
    target_language: str = "English"
) -> list[dict]:
    """
    Stage A (Search Result Ranking): Deterministically scores candidate URLs based on search metadata.
    1. Product name / synonym relevance (0-30)
    2. Manufacturer / official domain relevance (0-40)
    3. Part / Catalog / CAS number match (0-15)
    4. Direct SDS PDF / document type preference (0-15)
    5. Country / jurisdiction relevance (0-5)
    6. Language relevance (0-5)
    7. Trusted chemical domain bonus (0-10)
    8. Aggregator domain demotion (-35)
    """
    prod_norm = normalize_text(target_product)
    comp_norm = normalize_text(target_company)
    part_norm = normalize_identifier(target_part_number)
    cas_norm = normalize_identifier(target_cas)
    country_norm = normalize_text(target_country)
    lang_norm = normalize_text(target_language)

    authorized_domains = get_authorized_domains_for_manufacturer(target_company)

    ranked = []
    for cand in candidates:
        if not isinstance(cand, dict) or "error" in cand or not cand.get("url"):
            continue

        raw_url = str(cand.get("url", "")).strip()
        if not is_valid_url_syntax(raw_url):
            continue

        url_lower = raw_url.lower()
        title_lower = str(cand.get("title", "")).lower()
        snippet_lower = str(cand.get("snippet", "")).lower()
        combined_text = f"{title_lower} {snippet_lower}"

        try:
            parsed_netloc = urllib.parse.urlparse(url_lower).netloc.split(":")[0]
        except Exception:
            parsed_netloc = ""

        # 1. Product Match Score (0 - 30)
        prod_score = 0
        if prod_norm:
            if is_chemical_name_match(target_product, url_lower):
                prod_score = 30
            elif is_chemical_name_match(target_product, title_lower):
                prod_score = 28
            elif is_chemical_name_match(target_product, snippet_lower):
                prod_score = 22
            else:
                prod_tokens = extract_base_chemical_tokens(target_product)
                if prod_tokens:
                    token_matches = sum(1 for tok in prod_tokens if tok in combined_text or tok in url_lower)
                    prod_score = int(20 * (token_matches / len(prod_tokens)))

        # 2. Manufacturer Match Score (0 - 40)
        mfg_score = 0
        is_official_domain = False
        is_competing_domain = False

        if comp_norm:
            is_official_domain = any(
                parsed_netloc == ad or parsed_netloc.endswith("." + ad) for ad in authorized_domains
            )
            if is_official_domain:
                mfg_score = 40
            else:
                for mfg_key, doms in MANUFACTURER_DOMAINS.items():
                    norm_mfg_key = normalize_text(mfg_key)
                    if norm_mfg_key not in comp_norm and comp_norm not in norm_mfg_key and any(parsed_netloc == d or parsed_netloc.endswith("." + d) for d in doms):
                        is_competing_domain = True
                        break

                if not is_competing_domain:
                    if any(parsed_netloc == ts or parsed_netloc.endswith("." + ts) for ts in TRUSTED_SITES):
                        mfg_score = 15
                    elif comp_norm in title_lower:
                        mfg_score = 10
                    elif comp_norm in snippet_lower:
                        mfg_score = 5

        # 3. Part Number / CAS Number Score (0 - 15)
        part_cas_score = 0
        if cas_norm and (cas_norm in url_lower or cas_norm in normalize_identifier(combined_text)):
            part_cas_score = max(part_cas_score, 15)
        if part_norm and (part_norm in url_lower or part_norm in normalize_identifier(combined_text)):
            part_cas_score = max(part_cas_score, 15)

        # 4. Document Type / Direct PDF Score (0 - 15)
        doc_type_score = 0
        clean_url_path = url_lower.split("?")[0]
        if clean_url_path.endswith(".pdf") or "/pdf" in url_lower or "filetype=pdf" in url_lower or "directwebview" in url_lower:
            doc_type_score = 15
        elif any(s in url_lower for s in ["/sds/", "/msds/", "safety-data-sheet", "sds-search", "msds-search"]):
            doc_type_score = 10
        elif any(s in combined_text for s in ["safety data sheet", "sds pdf", "material safety data sheet"]):
            doc_type_score = 6

        # 5. Country / Jurisdiction Score (0 - 5)
        country_score = 0
        if country_norm:
            country_tokens = {
                "united states": ["us", "usa", "osha", "ansi", "united states", ".com"],
                "united kingdom": ["uk", "great britain", "clp", "reach", "hse", ".co.uk", ".uk"],
                "germany": ["germany", "deutschland", "de", "reach", "clp", "baua", ".de"],
                "france": ["france", "fr", "reach", "clp", ".fr"],
                "canada": ["canada", "ca", "whmis", ".ca"]
            }
            cand_tokens = country_tokens.get(country_norm, [country_norm])
            if any(tok in url_lower or tok in combined_text for tok in cand_tokens):
                country_score = 5

        # 6. Language Score (0 - 5)
        lang_score = 0
        if lang_norm:
            if lang_norm == "english" and any(w in combined_text for w in ["section", "hazard", "identification", "safety"]):
                lang_score = 5
            elif lang_norm in combined_text or lang_norm in url_lower:
                lang_score = 5

        # 7. Trusted Domain Bonus (0 - 10)
        trusted_bonus = 0
        if any(parsed_netloc == ts or parsed_netloc.endswith("." + ts) for ts in TRUSTED_SITES):
            trusted_bonus = 10

        # 8. Aggregator Demotion Penalty (-35)
        aggregator_penalty = 0
        if any(ad in parsed_netloc for ad in AGGREGATOR_DOMAINS):
            aggregator_penalty = -35

        total_score = prod_score + mfg_score + part_cas_score + doc_type_score + country_score + lang_score + trusted_bonus + aggregator_penalty
        final_score = max(0, min(100, total_score))

        reason_parts = []
        if is_official_domain:
            reason_parts.append("Official Manufacturer Domain")
        elif mfg_score >= 10:
            reason_parts.append("Manufacturer Match")
        if prod_score >= 20:
            reason_parts.append("Product Match")
        if part_cas_score > 0:
            reason_parts.append("CAS/Part Match")
        if doc_type_score >= 10:
            reason_parts.append("Direct SDS Document" if doc_type_score == 15 else "SDS Portal Link")
        if is_competing_domain:
            reason_parts.append("Competing Manufacturer Domain")
        if aggregator_penalty < 0:
            reason_parts.append("Demoted Aggregator Domain")

        selection_reason = ", ".join(reason_parts) if reason_parts else "General Candidate"

        ranked.append({
            "url": raw_url,
            "score": final_score,
            "title": cand.get("title", ""),
            "snippet": cand.get("snippet", ""),
            "source_query": cand.get("source_query", ""),
            "sub_scores": {
                "product_score": prod_score,
                "manufacturer_score": mfg_score,
                "part_cas_score": part_cas_score,
                "doc_type_score": doc_type_score,
                "country_score": country_score,
                "language_score": lang_score,
                "trusted_bonus": trusted_bonus,
                "aggregator_penalty": aggregator_penalty
            },
            "selection_reason": selection_reason
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)

def score_document_evidence(
    evidence: SDSEvidence,
    target_product: str,
    target_company: str,
    target_part_number: str = "",
    target_cas: str = "",
    target_country: str = "",
    target_language: str = "English"
) -> Tuple[int, Dict[str, Any], List[str]]:
    """
    Stage B (Document-First Evidence Ranking):
    Evaluates real extracted document evidence to compute a dominant evidence score (0-100).
    LEVEL 1: Real authentic GHS/OSHA SDS structure (0-25)
    LEVEL 2: Section 1 Product Name Match (0-35)
    LEVEL 3: Section 1 Manufacturer Match (0-30)
    LEVEL 4: Section 3 CAS / Part Number Match (0-15)
    LEVEL 5: Document Language & Jurisdiction Match (0-10)
    LEVEL 6: Direct PDF Format (0-10)
    """
    if not evidence or not evidence.fetched_successfully:
        return 0, {}, ["Document fetch failed or empty."]

    if not evidence.is_sds:
        return 0, {"is_sds": False}, ["Document lacks standard GHS/OSHA SDS headers."]

    doc_text = f"{evidence.product_name} {evidence.manufacturer} {evidence.raw_snippet} " + " ".join(evidence.sections.values())
    doc_lower = doc_text.lower()

    # 1. Structure Score
    structure_score = 25 if evidence.is_sds else 0

    # 2. Product Evidence Score (0 - 35)
    prod_evidence_score = 0
    if is_chemical_name_match(target_product, evidence.product_name):
        prod_evidence_score = 35
    elif is_chemical_name_match(target_product, doc_lower):
        prod_evidence_score = 30
    else:
        req_tokens = extract_base_chemical_tokens(target_product)
        if req_tokens:
            matches = sum(1 for t in req_tokens if t in doc_lower)
            prod_evidence_score = int(25 * (matches / len(req_tokens)))

    # 3. Manufacturer Evidence Score (0 - 30)
    mfg_evidence_score = 0
    auth_domains = get_authorized_domains_for_manufacturer(target_company)
    try:
        netloc = urllib.parse.urlparse(evidence.url.lower()).netloc.split(":")[0]
    except Exception:
        netloc = ""

    is_official = any(netloc == ad or netloc.endswith("." + ad) for ad in auth_domains)
    comp_norm = normalize_text(target_company)

    if is_official:
        mfg_evidence_score = 30
    elif comp_norm and comp_norm in normalize_text(evidence.manufacturer):
        if any(netloc == ts or netloc.endswith("." + ts) for ts in TRUSTED_SITES):
            mfg_evidence_score = 25
        else:
            mfg_evidence_score = 15
    elif comp_norm and comp_norm in doc_lower:
        mfg_evidence_score = 10

    # 4. CAS / Part Number Score (0 - 15)
    cas_part_score = 0
    norm_cas = normalize_identifier(target_cas)
    norm_part = normalize_identifier(target_part_number)

    if norm_cas and any(norm_cas == normalize_identifier(c) for c in evidence.cas_numbers):
        cas_part_score = max(cas_part_score, 15)
    elif norm_cas and norm_cas in normalize_identifier(doc_lower):
        cas_part_score = max(cas_part_score, 12)

    if norm_part and any(norm_part == normalize_identifier(p) for p in evidence.part_numbers):
        cas_part_score = max(cas_part_score, 15)

    # 5. Language & Jurisdiction (0 - 10)
    reg_score = 0
    if target_country and normalize_text(target_country) == normalize_text(evidence.country):
        reg_score += 5
    if target_language and normalize_text(target_language) == normalize_text(evidence.language):
        reg_score += 5

    # 6. Format (0 - 5)
    format_score = 5 if evidence.url_type == "pdf" else 2

    total = structure_score + prod_evidence_score + mfg_evidence_score + cas_part_score + reg_score + format_score
    doc_score = max(0, min(100, total))

    breakdown = {
        "structure_score": structure_score,
        "product_evidence_score": prod_evidence_score,
        "manufacturer_evidence_score": mfg_evidence_score,
        "cas_part_score": cas_part_score,
        "reg_score": reg_score,
        "format_score": format_score
    }

    reasons = []
    if structure_score >= 25:
        reasons.append("Authentic GHS SDS Structure")
    if prod_evidence_score >= 30:
        reasons.append("Verified Chemical Substance in Section 1")
    if mfg_evidence_score >= 25:
        reasons.append("Verified Manufacturer in Section 1 / Authorized Domain")
    if cas_part_score >= 12:
        reasons.append("Verified CAS/Part Identifier in Section 3")

    return doc_score, breakdown, reasons

@tool
def fetch_document_text(url: str) -> str:
    """
    Safely downloads and extracts structured Safety Data Sheet text from a URL (PDF or HTML).
    Includes full SSRF protection, redirect verification, stream bounds, and section extraction.
    Returns structured evidence summary containing product, manufacturer, sections, and CAS numbers.
    """
    try:
        data, content_type, final_url = safe_fetch_document(url, timeout=12.0)
        evidence = parse_sds_document(data, content_type, final_url)

        if not evidence.fetched_successfully:
            return f"Error fetching/parsing document: {evidence.error or 'Unknown parsing error'}"

        summary_lines = [
            f"--- SDS Document Evidence from: {final_url} ---",
            f"Is Authentic SDS: {evidence.is_sds}",
            f"Extracted Product: {evidence.product_name or 'Not specified'}",
            f"Extracted Manufacturer: {evidence.manufacturer or 'Not specified'}",
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
