"""
Chemical SDS Retrieval & Ranking Engine
=======================================
Architecture Role:
    Provides candidate search, multi-tier source classification, metadata candidate ranking,
    and extracted document evidence scoring for the LangGraph SDS retrieval agent.

Key Architectural Components:
    1. Multi-Tier Source Domain Taxonomy:
       - Tier 1: MANUFACTURER_DIRECT: Official chemical producer portals (e.g., sigmaaldrich.com, 3m.com, ecolab.com).
       - Tier 2: AUTHORIZED_DISTRIBUTOR: Vetted distributors (e.g., fishersci.com, vwr.com, avantorsciences.com).
       - Tier 3: INSTITUTIONAL_REPOSITORY: Regulatory & academic portals (e.g., echa.europa.eu, pubchem, osha.gov).
       - Tier 4: SECONDARY_HOST: Certified commercial SDS document hosts (e.g., msdsdigital.com, hazcoms.com).
       - Tier 5: LOW_TRUST_AGGREGATOR: Low-trust commercial scrapers (demoted by -35 penalty).
    2. Competing Manufacturer Demotion:
       Actively detects if a candidate URL originates from a recognized chemical manufacturer that
       differs from the requested manufacturer, suppressing competing company catalogs.
    3. Stage A - Search Result Ranking (rank_sds_candidates):
       Deterministic scoring (0-100) evaluating product keyword alignment, manufacturer authority,
       catalog/CAS tokens, direct PDF link syntax, and domain reputation.
    4. Stage B - Document-First Evidence Scoring (score_document_evidence):
       Direct assessment of parsed document contents, verifying standard 16 GHS/OSHA sections,
       Section 1 product trade name, Section 1 manufacturer identity, Section 3 ingredients/CAS,
       and regulatory jurisdiction.
    5. Packaging Token Stripping (strip_packaging_tokens):
       Removes commercial container, volume, and packaging descriptors (e.g., '500ml', 'drum', 'bottle')
       prior to web query generation to avoid landing on retail e-commerce sales pages.
"""

import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional, Set, Tuple
from langchain_core.tools import tool
from ddgs import DDGS

from src.core.security import safe_fetch_document, SecurityError, is_valid_url_syntax
from src.retrieval.sds_parser import (
    parse_sds_document,
    normalize_identifier,
    normalize_text,
    normalize_url,
    is_chemical_name_match,
    extract_base_chemical_tokens,
    MANUFACTURER_DOMAINS,
    is_pdf_content,
    is_pdf
)
from src.core.schema import SDSEvidence

# Tier 2: Authorized Chemical Distributors
AUTHORIZED_DISTRIBUTORS = {
    "fishersci.com",
    "fisherscientific.com",
    "vwr.com",
    "avantorsciences.com",
    "avantormaterials.com",
    "spectrumchemical.com",
    "airgas.com",
}

# Tier 3: Institutional, Regulatory & Safety Repositories
INSTITUTIONAL_REPOSITORIES = {
    "cdc.gov",
    "echa.europa.eu",
    "pubchem.ncbi.nlm.nih.gov",
    "ilpi.com",
    "osha.gov",
    "epa.gov",
    "nih.gov",
}

# Tier 4: Certified Secondary SDS Management Repositories (Inspected under strict verification)
SECONDARY_SDS_HOSTS = {
    "msdsdigital.com",
    "sdsinventory.com",
    "msdssolutions.com",
    "hazcoms.com",
}

# Tier 5: Low-Trust Commercial Lead-Gen Scrapers (Strictly demoted and rejected)
LOW_TRUST_AGGREGATORS = {
    "chemicalbook.com",
    "guidechem.com",
    "chemblink.com",
    "lookchem.com",
    "chemspider.com",
    "chemnet.com",
    "wikipedia.org",
    "sciencedirect.com",
    "cdhfinechemical.com",
    "labchem.com",
    "alfa-chem.com",
    "sdsmanager.com",
    "sds-manager.com",
}

# Backward compatible AGGREGATOR_DOMAINS (contains strictly low-trust scrapers)
AGGREGATOR_DOMAINS = list(LOW_TRUST_AGGREGATORS)

TRUSTED_SITES = [
    # Major Chemical & Lab Suppliers
    "sigmaaldrich.com",
    "sigma-aldrich.com",
    "fishersci.com",
    "fisherscientific.com",
    "thermofisher.com",
    "vwr.com",
    "avantorsciences.com",
    "avantormaterials.com",
    "merckmillipore.com",
    "milliporesigma.com",
    "emdmillipore.com",
    "merckgroup.com",
    "merck.com",
    "tcichemicals.com",
    "spectrumchemical.com",
    "scbt.com",
    "caymanchem.com",
    "caymanchemical.com",
    "bio-rad.com",
    "promega.com",
    "neb.com",
    "abcam.com",
    "cellsignal.com",
    # Industrial & Specialty Chemical Manufacturers
    "3m.com",
    "ecolab.com",
    "safetydata.ecolab.com",
    "dow.com",
    "basf.com",
    "dupont.com",
    "eastman.com",
    "evonik.com",
    "honeywell.com",
    "lab-honeywell.com",
    "sds.honeywell.com",
    "airgas.com",
    "linde.com",
    "linde-gas.com",
    "praxair.com",
    "mathesongas.com",
    "bayer.com",
    "cropscience.bayer.com",
    "airliquide.com",
    # Institutional & Safety Portals
    "cdc.gov",
    "echa.europa.eu",
    "ilpi.com",
    "msdssolutions.com",
    "pubchem.ncbi.nlm.nih.gov",
]

def get_source_tier(netloc: str) -> str:
    """Classifies a hostname into one of five structured source tiers."""
    clean_netloc = netloc.lower().split(":")[0].strip()
    if any(clean_netloc == dom or clean_netloc.endswith("." + dom) for doms in MANUFACTURER_DOMAINS.values() for dom in doms):
        return "MANUFACTURER_DIRECT"
    if any(clean_netloc == ad or clean_netloc.endswith("." + ad) for ad in AUTHORIZED_DISTRIBUTORS):
        return "AUTHORIZED_DISTRIBUTOR"
    if any(clean_netloc == ir or clean_netloc.endswith("." + ir) for ir in INSTITUTIONAL_REPOSITORIES) or clean_netloc.endswith(".edu") or clean_netloc.endswith(".gov"):
        return "INSTITUTIONAL_REPOSITORY"
    if any(clean_netloc == sh or clean_netloc.endswith("." + sh) for sh in SECONDARY_SDS_HOSTS):
        return "SECONDARY_HOST"
    if any(clean_netloc == lta or clean_netloc.endswith("." + lta) for lta in LOW_TRUST_AGGREGATORS):
        return "LOW_TRUST_AGGREGATOR"
    return "UNKNOWN"

# Packaging, container, and physical size/volume descriptors that interfere with SDS discovery
PACKAGING_CONTAINER_PATTERN = re.compile(
    r'\b(?:\d+(?:\.\d+)?\s*(?:ml|l|liter|liters|litre|litres|kg|g|mg|gal|gallon|gallons|oz|fl\s*oz|lb|lbs|pt|qt)\b|'
    r'bottle|bottles|drum|drums|container|containers|package|packages|packaging|'
    r'vial|vials|ampul|ampule|ampules|ampoule|ampoules|pail|pails|canister|canisters|carboy|carboys)\b',
    re.IGNORECASE
)

def strip_packaging_tokens(text: str) -> str:
    """
    Normalizes search query text by removing commercial packaging, container types,
    and bulk quantity/size descriptors (e.g., '500ml', '1kg', 'bottle', 'drum').
    Preserves chemical identity and concentration modifiers (e.g., '37%', 'anhydrous', '200 proof').
    """
    if not text:
        return ""
    cleaned = PACKAGING_CONTAINER_PATTERN.sub(' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else text

def get_authorized_domains_for_manufacturer(manufacturer_name: str) -> List[str]:
    """Returns official or authorized domain list for a chemical manufacturer."""
    clean_mfg = normalize_text(manufacturer_name)
    if not clean_mfg:
        return []

    domains: List[str] = []
    for key, doms in MANUFACTURER_DOMAINS.items():
        norm_key = normalize_text(key)
        if norm_key in clean_mfg or clean_mfg in norm_key:
            for d in doms:
                if d not in domains:
                    domains.append(d)

    if not domains:
        comp_token = re.sub(r'[^a-z0-9]', '', clean_mfg)
        if comp_token and len(comp_token) > 3:
            domains.append(f"{comp_token}.com")

    return domains

def generate_retrieval_queries(
    product: str,
    company: str,
    part_number: str = "",
    cas: str = "",
    country: str = "",
    language: str = "English"
) -> List[str]:
    """
    Generates a prioritized, multi-level list of orthogonal search queries for chemical SDS discovery:
    Level 1: Exact Substance & Manufacturer Direct PDF
    Level 2: Exact GHS Safety Data Sheet Title
    Level 3: Clean Substance & Manufacturer SDS
    Level 4: CAS / Part Number Specific Discovery
    Level 5: Broad Chemical Safety Data Sheet Search (Manufacturer-Agnostic Fallback)
    Level 6: Domain-Targeted Retrieval (Manufacturer Direct & Authorized Distributor site: queries)
    """
    prod_clean = re.sub(r'["\r\n\t]', ' ', product).strip()
    prod_search = strip_packaging_tokens(prod_clean)
    if not prod_search:
        prod_search = prod_clean

    comp_clean = re.sub(r'["\r\n\t]', ' ', company).strip()
    part_clean = re.sub(r'["\r\n\t]', '', part_number).strip() if part_number and not part_number.startswith("http") else ""
    cas_clean = cas.strip() if cas and re.match(r'^\d{2,7}-\d{2}-\d$', cas.strip()) else ""

    auth_domains = get_authorized_domains_for_manufacturer(company)
    queries: List[str] = []

    # Level 1: Exact Substance & Manufacturer Direct PDF
    if comp_clean and prod_search:
        queries.append(f'"{prod_search}" "{comp_clean}" SDS PDF')

    # Level 2: Exact GHS Safety Data Sheet Title
    if comp_clean and prod_search:
        queries.append(f'"{prod_search}" "{comp_clean}" "Safety Data Sheet"')

    # Level 3: Clean Substance & Manufacturer SDS
    if comp_clean and prod_search:
        queries.append(f"{comp_clean} {prod_search} SDS")

    # Level 4: CAS / Part Number Specific Discovery
    if comp_clean and prod_search and cas_clean:
        queries.append(f'"{prod_search}" "{cas_clean}" SDS')
        queries.append(f"{comp_clean} {prod_search} {cas_clean} SDS PDF")
    elif comp_clean and prod_search and part_clean:
        queries.append(f'"{prod_search}" "{part_clean}" SDS')
        queries.append(f"{comp_clean} {prod_search} {part_clean} SDS")

    # Level 5: Broad Chemical Safety Data Sheet Search (fallback)
    if prod_search:
        queries.append(f'"{prod_search}" SDS PDF')

    # Level 6: Domain-Targeted Retrieval
    # 6A: Targeted Official Manufacturer Domain Queries
    if auth_domains and prod_search:
        for dom in auth_domains[:2]:
            queries.append(f"site:{dom} {prod_search} SDS")
    # 6B: Authorized Distributor Domain Queries
    if prod_search and comp_clean:
        queries.append(f"site:fishersci.com {prod_search} SDS")
        queries.append(f"site:vwr.com {prod_search} SDS")

    # Regional / Country Explicit Query
    country_clean = country.strip() if country else ""
    if country_clean and country_clean.lower() not in ["united states", "usa", "us"] and prod_search and comp_clean:
        queries.append(f"{comp_clean} {prod_search} {country_clean} SDS")

    # Deduplicate while strictly preserving priority order
    seen: Set[str] = set()
    deduped: List[str] = []
    for q in queries:
        q_norm = q.strip()
        if q_norm and q_norm.lower() not in seen:
            seen.add(q_norm.lower())
            deduped.append(q_norm)

    return deduped

@tool
def search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """
    Executes a targeted web search using DuckDuckGo to discover candidate Safety Data Sheets.
    Applies query packaging token normalization and a conservative backoff retry for transient failures.
    Returns a deduplicated list of search results containing url, snippet, and title.
    """
    if not query or not isinstance(query, str) or not query.strip():
        return []

    # Clean packaging/container tokens to prevent commercial catalog interference
    search_query = strip_packaging_tokens(query.strip())
    if not search_query:
        search_query = query.strip()

    results = []
    unique_urls = set()
    last_err: Optional[Exception] = None

    for attempt in range(2):  # Maximum 1 retry (2 total attempts)
        try:
            with DDGS() as ddgs:
                search_res = ddgs.text(search_query, max_results=max_results)
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
                return results

        except Exception as e:
            last_err = e
            err_msg = str(e).lower()
            # Do not retry permanent security or validation errors
            if "security" in err_msg or "ssrf" in err_msg or "invalid url" in err_msg:
                return [{"error": f"Search validation error: {str(e)}"}]

            # Conservative retry for transient failures (attempt 0 only)
            if attempt == 0:
                time.sleep(1.0)  # ~1 second backoff delay
                continue
            else:
                return [{"error": f"Search failed after transient retry: {str(last_err)}"}]

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

        # 2. Manufacturer Match Score (0 - 40) via Structured Tier Classification
        mfg_score = 0
        tier = get_source_tier(parsed_netloc)
        is_official_domain = any(
            parsed_netloc == ad or parsed_netloc.endswith("." + ad) for ad in authorized_domains
        )
        is_authorized_distributor = (tier == "AUTHORIZED_DISTRIBUTOR")
        is_institutional = (tier == "INSTITUTIONAL_REPOSITORY")
        is_secondary_host = (tier == "SECONDARY_HOST")
        is_low_trust = (tier == "LOW_TRUST_AGGREGATOR") or any(ad in parsed_netloc for ad in LOW_TRUST_AGGREGATORS)
        is_competing_domain = False

        if comp_norm:
            if is_official_domain:
                mfg_score = 40
            else:
                for mfg_key, doms in MANUFACTURER_DOMAINS.items():
                    norm_mfg_key = normalize_text(mfg_key)
                    if norm_mfg_key not in comp_norm and comp_norm not in norm_mfg_key and any(parsed_netloc == d or parsed_netloc.endswith("." + d) for d in doms):
                        is_competing_domain = True
                        break

                if not is_competing_domain:
                    if is_authorized_distributor:
                        mfg_score = 25
                    elif is_institutional:
                        mfg_score = 18
                    elif is_secondary_host:
                        mfg_score = 12
                    elif any(parsed_netloc == ts or parsed_netloc.endswith("." + ts) for ts in TRUSTED_SITES):
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
        if not is_competing_domain:
            if is_official_domain or is_authorized_distributor or is_institutional:
                trusted_bonus = 10
            elif is_secondary_host or any(parsed_netloc == ts or parsed_netloc.endswith("." + ts) for ts in TRUSTED_SITES):
                trusted_bonus = 5

        # 8. Aggregator Demotion Penalty (-35) - Strictly for LOW_TRUST_AGGREGATORS
        aggregator_penalty = 0
        if is_low_trust:
            aggregator_penalty = -35

        total_score = prod_score + mfg_score + part_cas_score + doc_type_score + country_score + lang_score + trusted_bonus + aggregator_penalty
        final_score = max(0, min(100, total_score))

        reason_parts = []
        if is_competing_domain:
            reason_parts.append("Competing Manufacturer Demoted")
        elif is_official_domain:
            reason_parts.append("Official Manufacturer Domain")
        elif is_authorized_distributor:
            reason_parts.append("Authorized Distributor")
        elif is_institutional:
            reason_parts.append("Institutional Repository")
        elif is_secondary_host:
            reason_parts.append("Secondary SDS Host")
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
    doc_norm = normalize_text(doc_text)

    # 1. Structure Score
    structure_score = 25 if evidence.is_sds else 0

    # 2. Product Evidence Score (0 - 35)
    prod_evidence_score = 0
    if is_chemical_name_match(target_product, evidence.product_name):
        prod_evidence_score = 35
    elif is_chemical_name_match(target_product, doc_norm) or is_chemical_name_match(target_product, doc_lower):
        prod_evidence_score = 30
    else:
        req_tokens = extract_base_chemical_tokens(target_product)
        if req_tokens:
            matches = sum(1 for t in req_tokens if t in doc_norm or t in doc_lower)
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
    elif comp_norm and (comp_norm in normalize_text(evidence.manufacturer) or comp_norm in doc_norm):
        if any(netloc == ts or netloc.endswith("." + ts) for ts in TRUSTED_SITES):
            mfg_evidence_score = 25
        else:
            mfg_evidence_score = 20
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
