import re
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any
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

SDS_MARKERS = [
    "safety data sheet",
    "material safety data sheet",
    "sds",
    "msds",
    "fiche de donnees de securite",
    "sicherheitsdatenblatt",
    "identification of the substance",
    "hazards identification",
    "composition/information on ingredients",
    "ghs classification"
]

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
        # Remove default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]
        path = parsed.path.rstrip("/")
        # Rebuild URL
        clean_url = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, parsed.query, ''))
        return clean_url
    except Exception:
        return url.strip().rstrip("/")

def extract_sds_sections(full_text: str) -> Dict[str, str]:
    """Splits full document text into standard 16 GHS / OSHA SDS sections."""
    sections: Dict[str, str] = {}

    # Common section header patterns
    patterns = {
        "section_1_identification": r'(?:section\s*1[:.]?\s*(?:identification|chemical product)|1\.\s*identification)',
        "section_2_hazards": r'(?:section\s*2[:.]?\s*(?:hazard|hazards identification)|2\.\s*hazard)',
        "section_3_composition": r'(?:section\s*3[:.]?\s*(?:composition|ingredient)|3\.\s*composition)',
        "section_4_first_aid": r'(?:section\s*4[:.]?\s*first[ -]aid|4\.\s*first[ -]aid)',
        "section_9_physical": r'(?:section\s*9[:.]?\s*physical|9\.\s*physical)',
        "section_15_regulatory": r'(?:section\s*15[:.]?\s*regulatory|15\.\s*regulatory)',
        "section_16_other": r'(?:section\s*16[:.]?\s*other|16\.\s*other)',
    }

    # Find section positions
    found_spans = []
    for sec_name, pattern in patterns.items():
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            found_spans.append((match.start(), sec_name))

    found_spans.sort(key=lambda x: x[0])

    for i, (start_idx, sec_name) in enumerate(found_spans):
        end_idx = found_spans[i + 1][0] if i + 1 < len(found_spans) else len(full_text)
        sec_chunk = full_text[start_idx:end_idx].strip()
        sections[sec_name] = sec_chunk[:1500]

    return sections

def parse_sds_document(
    raw_data: bytes,
    content_type: str,
    url: str,
    max_pdf_pages: int = 6
) -> SDSEvidence:
    """
    Parses raw bytes of an SDS document (PDF or HTML), extracting structured fields,
    CAS numbers, part numbers, revision dates, and sections.
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
    is_sds = any(marker in norm_full for marker in SDS_MARKERS)
    cas_matches = list(set(CAS_REGEX.findall(full_text)))
    part_matches = list(set(PART_NUMBER_REGEX.findall(full_text)))
    date_match = DATE_REGEX.search(full_text)
    revision_date = date_match.group(1) if date_match else ""
    sections = extract_sds_sections(full_text)

    language = "English"
    if "fiche de donnees" in norm_full or "rubrique 1" in norm_full:
        language = "French"
    elif "sicherheitsdatenblatt" in norm_full or "abschnitt 1" in norm_full:
        language = "German"
    elif "hoja de datos de seguridad" in norm_full:
        language = "Spanish"

    country = "United States"
    if "osha" in norm_full or "cfr 1910.1200" in norm_full:
        country = "United States"
    elif "reach" in norm_full or "clp" in norm_full or "ec no" in norm_full:
        country = "European Union"
    elif "whmis" in norm_full or "canada" in norm_full:
        country = "Canada"

    raw_snippet = full_text[:2500]

    return SDSEvidence(
        url=url,
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
