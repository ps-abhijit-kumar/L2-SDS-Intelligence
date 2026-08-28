import re
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any, Set
import pymupdf as fitz
from bs4 import BeautifulSoup

from src.schema import SDSEvidence

CAS_REGEX = re.compile(r'\b[1-9]\d{1,6}-\d{2}-\d\b')
DATE_REGEX = re.compile(
    r'(?:revision\s*date|revised\s*on|issue\s*date|date\s*of\s*issue|print\s*date)[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})',
    re.IGNORECASE
)
PART_NUMBER_REGEX = re.compile(
    r'(?:catalog\s*(?:no|number|#)?|part\s*(?:no|number|#)?|product\s*(?:no|number|#|code)?|item\s*(?:no|number|#)?)[:\s]*([A-Za-z0-9_.-]{3,30})',
    re.IGNORECASE
)

PRODUCT_NAME_PATTERNS = [
    re.compile(r'(?:1\.1\s*(?:product\s*identifier|product\s*name)|product\s*name|trade\s*name|material\s*name|substance\s*name|chemical\s*name)[:\s]*([^\n\r;]{3,100})', re.IGNORECASE),
    re.compile(r'(?:product\s*description|product\s*code\s*and\s*name)[:\s]*([^\n\r;]{3,100})', re.IGNORECASE),
    re.compile(r'SAFETY\s+DATA\s+SHEET\s*\n+([A-Z0-9\s,%()/-]{3,80})\n', re.IGNORECASE)
]

MANUFACTURER_PATTERNS = [
    re.compile(r'(?:1\.3\s*(?:details\s*of\s*the\s*supplier|supplier)|manufacturer|supplier|company\s*name|produced\s*by|distributed\s*by)[:\s]*([^\n\r;]{3,100})', re.IGNORECASE),
    re.compile(r'(?:supplier\s*address|distributor)[:\s]*([^\n\r;]{3,100})', re.IGNORECASE)
]

SDS_MARKERS = [
    "safety data sheet",
    "material safety data sheet",
    "sds",
    "msds",
    "fiche de donnees de securite",
    "fiche de données de sécurité",
    "sicherheitsdatenblatt",
    "identification of the substance",
    "hazards identification",
    "composition/information on ingredients",
    "ghs classification",
    "hazard communication standard"
]

CHEMICAL_SYNONYMS: Dict[str, List[str]] = {
    "acetone": ["acetone", "2 propanone", "propan 2 one", "dimethyl ketone", "pyroacetic ether", "beta ketopropane"],
    "isopropyl alcohol": ["isopropanol", "isopropyl alcohol", "2 propanol", "propan 2 ol", "ipa", "sec propyl alcohol", "rubbing alcohol", "1 methylethanol"],
    "methanol": ["methyl alcohol", "methanol", "wood alcohol", "carbinol", "methyl hydrate", "wood spirits", "hydroxymethane"],
    "ethanol": ["ethyl alcohol", "ethanol", "grain alcohol", "absolute alcohol", "alcohol anhydrous", "ethyl hydrate"],
    "ethanol 200 proof": ["ethanol", "ethyl alcohol", "ethyl alcohol 200 proof", "absolute alcohol", "ethanol 100", "ethanol 200 proof", "ethyl alcohol anhydrous", "grain alcohol"],
    "sulfuric acid": ["sulfuric acid", "sulphuric acid", "oil of vitriol", "hydrogen sulfate", "vitriol brown oil", "battery acid", "dihydrogen sulfate"],
    "hydrochloric acid": ["hydrochloric acid", "muriatic acid", "hydrogen chloride aqueous", "chlorohydric acid", "hydrogen chloride", "aqueous hydrogen chloride"],
    "hydrochloric acid 37": ["hydrochloric acid", "hydrochloric acid 37", "muriatic acid", "hydrogen chloride", "hydrochloric acid 37 percent", "aqueous hydrogen chloride"],
    "nitric acid": ["nitric acid", "aqua fortis", "hydrogen nitrate", "nitryl hydroxide", "spirit of nitre"],
    "toluene": ["toluene", "methylbenzene", "toluol", "phenylmethane", "tolu-sol", "methacide"],
    "benzene": ["benzene", "benzol", "cyclohexatriene", "coal naphtha", "phenyl hydride"],
    "sodium hydroxide": ["sodium hydroxide", "caustic soda", "lye", "sodium hydrate", "white caustic", "soda lye"]
}

CHEMICAL_GRADE_MODIFIERS = {
    "acs", "reagent", "grade", "pure", "puriss", "anhydrous", "solution",
    "aqueous", "percentage", "proof", "200", "37", "99", "95", "98",
    "for", "analysis", "hplc", "spectroscopy", "trace", "metal", "extra"
}

def normalize_text(text: str) -> str:
    """Normalizes text by lowercasing and stripping non-alphanumeric chars."""
    if not text:
        return ""
    return re.sub(r'[^a-z0-9\s]', ' ', str(text).lower()).strip()

def normalize_identifier(identifier: str) -> str:
    """Strictly normalizes a part number, catalog number, or CAS number."""
    if not identifier:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(identifier)).lower()

def normalize_url(url: str) -> str:
    """Canonicalizes a URL for deterministic provenance comparison."""
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]
        path = parsed.path.rstrip("/")
        clean_url = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, parsed.query, ''))
        return clean_url
    except Exception:
        return url.strip().rstrip("/")

def extract_base_chemical_tokens(product_name: str) -> List[str]:
    """Extracts essential chemical noun tokens, stripping grades, percentages, and qualifiers."""
    norm = normalize_text(product_name)
    tokens = [t for t in norm.split() if t not in CHEMICAL_GRADE_MODIFIERS and len(t) > 2]
    return tokens

def is_chemical_name_match(requested_product: str, candidate_text: str) -> bool:
    """
    Determines if candidate document text or extracted product matches the requested chemical,
    accounting for chemical synonyms, primary chemical nouns, and concentration grades.
    """
    req_norm = normalize_text(requested_product)
    cand_norm = normalize_text(candidate_text)
    if not req_norm or not cand_norm:
        return False

    # 1. Exact string containment
    if req_norm in cand_norm:
        return True

    # 2. Known chemical synonyms
    for canonical, syn_list in CHEMICAL_SYNONYMS.items():
        can_norm = normalize_text(canonical)
        if can_norm == req_norm or can_norm in req_norm or req_norm in can_norm:
            for syn in syn_list:
                syn_norm = normalize_text(syn)
                if syn_norm and (syn_norm in cand_norm or cand_norm in syn_norm):
                    return True

    # 3. Base chemical token matching (stripping concentration grades like 37%, 200 proof, 99%)
    req_tokens = extract_base_chemical_tokens(requested_product)
    if req_tokens:
        matched = sum(1 for t in req_tokens if t in cand_norm)
        if (matched / len(req_tokens)) >= 0.7:
            return True

    return False

def extract_sds_sections(full_text: str) -> Dict[str, str]:
    """Splits full document text into standard 16 GHS / OSHA SDS sections."""
    sections: Dict[str, str] = {}

    patterns = {
        "section_1_identification": r'(?:section\s*1[:.]?\s*(?:identification|chemical product)|1\.\s*identification)',
        "section_2_hazards": r'(?:section\s*2[:.]?\s*(?:hazard|hazards identification)|2\.\s*hazard)',
        "section_3_composition": r'(?:section\s*3[:.]?\s*(?:composition|ingredient)|3\.\s*composition)',
        "section_4_first_aid": r'(?:section\s*4[:.]?\s*first[ -]aid|4\.\s*first[ -]aid)',
        "section_5_fire_fighting": r'(?:section\s*5[:.]?\s*fire|5\.\s*fire)',
        "section_6_accidental_release": r'(?:section\s*6[:.]?\s*accidental|6\.\s*accidental)',
        "section_7_handling_storage": r'(?:section\s*7[:.]?\s*handling|7\.\s*handling)',
        "section_8_exposure_controls": r'(?:section\s*8[:.]?\s*exposure|8\.\s*exposure)',
        "section_9_physical": r'(?:section\s*9[:.]?\s*physical|9\.\s*physical)',
        "section_10_stability_reactivity": r'(?:section\s*10[:.]?\s*stability|10\.\s*stability)',
        "section_11_toxicological": r'(?:section\s*11[:.]?\s*toxicological|11\.\s*toxicological)',
        "section_12_ecological": r'(?:section\s*12[:.]?\s*ecological|12\.\s*ecological)',
        "section_13_disposal": r'(?:section\s*13[:.]?\s*disposal|13\.\s*disposal)',
        "section_14_transport": r'(?:section\s*14[:.]?\s*transport|14\.\s*transport)',
        "section_15_regulatory": r'(?:section\s*15[:.]?\s*regulatory|15\.\s*regulatory)',
        "section_16_other": r'(?:section\s*16[:.]?\s*other|16\.\s*other)',
    }

    found_spans = []
    for sec_name, pattern in patterns.items():
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            found_spans.append((match.start(), sec_name))

    found_spans.sort(key=lambda x: x[0])

    for i, (start_idx, sec_name) in enumerate(found_spans):
        end_idx = found_spans[i + 1][0] if i + 1 < len(found_spans) else len(full_text)
        sec_chunk = full_text[start_idx:end_idx].strip()
        sections[sec_name] = sec_chunk[:2500]

    return sections

def detect_document_language(full_text: str) -> str:
    """
    Deterministically detects document language from body text markers across 16 SDS sections.
    """
    norm = full_text.lower()

    if "sicherheitsdatenblatt" in norm or "abschnitt 1" in norm or "bezeichnung des stoffs" in norm or "mögliche gefahren" in norm:
        return "German"
    elif "fiche de donnees" in norm or "fiche de données" in norm or "rubrique 1" in norm or "identification de la substance" in norm:
        return "French"
    elif "hoja de datos de seguridad" in norm or "sección 1" in norm or "identificación de la sustancia" in norm:
        return "Spanish"
    elif "scheda di dati di sicurezza" in norm or "sezione 1" in norm or "identificazione della sostanza" in norm:
        return "Italian"
    elif "veiligheidsinformatieblad" in norm or "rubriek 1" in norm:
        return "Dutch"
    elif "safety data sheet" in norm or "section 1" in norm or "hazards identification" in norm or "composition" in norm:
        return "English"

    return "English"

def detect_document_jurisdiction(full_text: str, sections: Dict[str, str]) -> str:
    """
    Evidence-based detection of country/jurisdiction from Section 15 Regulatory Information
    and document body standards.
    """
    norm_full = full_text.lower()
    sec15 = sections.get("section_15_regulatory", "").lower()
    reg_text = f"{norm_full} {sec15}"

    if "osha" in reg_text or "29 cfr 1910.1200" in reg_text or "hcs 2012" in reg_text or "ansi z400" in reg_text or "sara title iii" in reg_text or "tsca" in reg_text or "nfpa 704" in reg_text:
        return "United States"
    elif "whmis" in reg_text or "hazardous products regulations" in reg_text or "sor/2015-17" in reg_text or "dsl/ndsl" in reg_text:
        return "Canada"
    elif "uk reach" in reg_text or "gb reach" in reg_text or "gb clp" in reg_text or "health and safety executive" in reg_text or "coshh" in reg_text:
        return "United Kingdom"
    elif "reach" in reg_text or "clp" in reg_text or "1907/2006" in reg_text or "1272/2008" in reg_text or "baua" in reg_text or "echa" in reg_text or "gefstoffv" in reg_text or "wgk" in reg_text:
        return "European Union"

    return "United States"

def parse_sds_document(
    raw_data: bytes,
    content_type: str,
    url: str,
    max_pdf_pages: int = 10
) -> SDSEvidence:
    """
    Parses raw bytes of an SDS document (PDF or HTML), extracting structured fields,
    product name, manufacturer, CAS numbers, part numbers, revision dates, and sections.
    """
    is_pdf = 'application/pdf' in content_type.lower() or url.lower().split('?')[0].endswith('.pdf')
    full_text = ""

    try:
        if is_pdf:
            doc = fitz.open(stream=raw_data, filetype="pdf")
            num_pages = len(doc)
            pages_to_read = min(num_pages, max_pdf_pages)

            page_texts = []
            for page_num in range(pages_to_read):
                text = doc[page_num].get_text()
                if text:
                    page_texts.append(text)

            full_text = "\n\n".join(page_texts)
        else:
            soup = BeautifulSoup(raw_data, 'html.parser')
            for elem in soup(["script", "style", "nav", "footer"]):
                elem.decompose()
            full_text = soup.get_text(separator=' ', strip=True)

    except Exception as parse_err:
        return SDSEvidence(
            url=url,
            raw_snippet="",
            error=f"Failed to parse document: {str(parse_err)}",
            fetched_successfully=False
        )

    if not full_text or len(full_text.strip()) == 0:
        return SDSEvidence(
            url=url,
            raw_snippet="",
            error="Document contained no extractable text.",
            fetched_successfully=False
        )

    norm_full = full_text.lower()
    is_sds = any(marker in norm_full for marker in SDS_MARKERS) or "section 1" in norm_full or "section 2" in norm_full
    cas_matches = list(set(CAS_REGEX.findall(full_text)))
    part_matches = list(set(PART_NUMBER_REGEX.findall(full_text)))
    date_match = DATE_REGEX.search(full_text)
    revision_date = date_match.group(1).strip() if date_match else ""
    sections = extract_sds_sections(full_text)

    # Extract Product Name from Section 1 or headers
    product_name = ""
    for pat in PRODUCT_NAME_PATTERNS:
        match = pat.search(full_text)
        if match:
            product_name = match.group(1).strip()
            break

    if not product_name and "section_1_identification" in sections:
        sec1 = sections["section_1_identification"]
        for pat in PRODUCT_NAME_PATTERNS:
            match = pat.search(sec1)
            if match:
                product_name = match.group(1).strip()
                break

    # Extract Manufacturer from Section 1 or headers
    manufacturer = ""
    for pat in MANUFACTURER_PATTERNS:
        match = pat.search(full_text)
        if match:
            manufacturer = match.group(1).strip()
            break

    if not manufacturer and "section_1_identification" in sections:
        sec1 = sections["section_1_identification"]
        for pat in MANUFACTURER_PATTERNS:
            match = pat.search(sec1)
            if match:
                manufacturer = match.group(1).strip()
                break

    language = detect_document_language(full_text)
    country = detect_document_jurisdiction(full_text, sections)

    url_type = "pdf" if is_pdf else "landing_page"
    raw_snippet = full_text[:1500].strip()

    return SDSEvidence(
        url=url,
        url_type=url_type,
        product_name=product_name,
        manufacturer=manufacturer,
        part_numbers=part_matches[:10],
        cas_numbers=cas_matches[:10],
        revision_date=revision_date,
        language=language,
        country=country,
        is_sds=is_sds,
        sections=sections,
        raw_snippet=raw_snippet,
        error=None,
        fetched_successfully=True
    )
