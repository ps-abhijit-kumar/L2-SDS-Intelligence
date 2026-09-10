"""
Chemical SDS Document Parser & Entity Extraction
================================================
Architecture Role:
    Provides robust parsing, content-type verification, and entity extraction
    for candidate Safety Data Sheet documents in both binary PDF and HTML formats.

Key Capabilities:
    1. Multi-Format Text Extraction:
       - PDF Extraction: Employs PyMuPDF (fitz) with bounded page reading (default up to 10 pages)
         to extract clean text layers without excessive memory allocation.
       - HTML Parsing: Employs BeautifulSoup, decomposing navigational, styling, header, and footer
         tags to isolate genuine product/hazard text.
    2. GHS / OSHA 16-Section Segmentation (extract_sds_sections):
       Identifies standard hazard communication section headers (Sections 1 through 16),
       segmenting Section 1 (Identification), Section 2 (Hazards), Section 3 (Composition),
       and Section 15 (Regulatory) into bounded text chunks for downstream verification.
    3. Chemical Entity & Synonym Matching (is_chemical_name_match):
       Cross-references an extensive chemical synonym map (e.g. acetone <-> 2-propanone <-> dimethyl ketone)
       and strips commercial grade qualifiers ('reagent', 'anhydrous', '200 proof', '37%')
       via `extract_base_chemical_tokens` to prevent false mismatches.
    4. Deterministic Language & Jurisdiction Classification:
       - detect_document_language: Matches authentic multi-lingual SDS terms (English, German,
         French, Spanish, Italian, Dutch).
       - detect_document_jurisdiction: Detects regulatory authority references (OSHA/HCS 2012 for US,
         WHMIS for Canada, UK REACH/COSHH for UK, REACH/CLP/ECHA for EU).
    5. %PDF Magic Byte Validation (is_pdf_content):
       Inspects initial binary bytes for '%PDF' header marker, ensuring robust type detection
       regardless of misleading HTTP Content-Type headers or URL query string extensions.
"""

import re
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any, Set
import pymupdf as fitz
from bs4 import BeautifulSoup

from src.core.schema import SDSEvidence

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
    re.compile(r'(?:1\.3\s*(?:details\s*of\s*the\s*supplier|supplier)|manufacturer|supplier|company(?:\s*name)?(?!\s*information)|brand|produced\s*by|distributed\s*by)[:\s]+([A-Za-z0-9][^\n\r;]{2,80})', re.IGNORECASE),
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
    "sodium hydroxide": ["sodium hydroxide", "caustic soda", "lye", "sodium hydrate", "white caustic", "soda lye"],
    "dichloromethane": ["dichloromethane", "methylene chloride", "methylene dichloride", "dcm", "methane dichloride"],
    "acetonitrile": ["acetonitrile", "methyl cyanide", "cyanomethane", "ethyl nitrile", "acn"],
    "tetrahydrofuran": ["tetrahydrofuran", "thf", "oxolane", "1 4 epoxybutane", "diethylene oxide", "tetramethylene oxide"],
    "acetic acid": ["acetic acid", "ethanoic acid", "glacial acetic acid", "vinegar acid", "methanecarboxylic acid"],
    "hydrogen peroxide": ["hydrogen peroxide", "dihydrogen dioxide", "dioxidane", "peroxide", "hydroperoxide"],
    "phosphoric acid": ["phosphoric acid", "orthophosphoric acid", "trihydroxylphosphine oxide", "hydrogen phosphate"],
    "potassium hydroxide": ["potassium hydroxide", "caustic potash", "potash lye", "potassium hydrate"],
    "ammonium hydroxide": ["ammonium hydroxide", "ammonia aqueous", "aqueous ammonia", "ammonia solution", "ammoniacal liquor"],
    "hexane": ["hexane", "n hexane", "normal hexane", "dipropyl", "hexyl hydride"],
    "ethyl acetate": ["ethyl acetate", "acetic acid ethyl ester", "ethyl ethanoate", "acetoxyethane", "etac"],
    "chloroform": ["chloroform", "trichloromethane", "formyl trichloride", "methane trichloride"],
    "dimethyl sulfoxide": ["dimethyl sulfoxide", "dmso", "methyl sulfoxide", "dimethylsulfoxide", "sulfinylbismethane"],
    "dimethylformamide": ["dimethylformamide", "n n dimethylformamide", "dmf", "n n dimethylmethanamide"],
    "formaldehyde": ["formaldehyde", "formalin", "methanal", "methylene oxide", "methyl aldehyde", "oxomethane"]
}

MANUFACTURER_DOMAINS: Dict[str, List[str]] = {
    "sigma aldrich": ["sigmaaldrich.com", "merckmillipore.com", "milliporesigma.com", "emdmillipore.com", "sigma-aldrich.com"],
    "sigma": ["sigmaaldrich.com", "merckmillipore.com", "milliporesigma.com"],
    "aldrich": ["sigmaaldrich.com", "merckmillipore.com"],
    "merck": ["merckmillipore.com", "sigmaaldrich.com", "merckgroup.com", "emdmillipore.com", "merck.com"],
    "fisher scientific": ["fishersci.com", "thermofisher.com", "fisherscientific.com"],
    "fisher": ["fishersci.com", "thermofisher.com", "fisherscientific.com"],
    "thermo fisher": ["thermofisher.com", "fishersci.com", "alfa.com", "acros.com"],
    "thermo": ["thermofisher.com", "fishersci.com"],
    "alfa aesar": ["alfa.com", "thermofisher.com"],
    "acros organics": ["acros.com", "thermofisher.com"],
    "honeywell": ["honeywell.com", "lab-honeywell.com", "sds.honeywell.com"],
    "spectrum chemical": ["spectrumchemical.com", "fishersci.com", "sigmaaldrich.com"],
    "spectrum": ["spectrumchemical.com", "fishersci.com"],
    "avantor": ["avantorsciences.com", "vwr.com", "sigmaaldrich.com", "avantormaterials.com"],
    "vwr": ["vwr.com", "avantorsciences.com"],
    "tci chemicals": ["tcichemicals.com", "tokyokasei.co.jp"],
    "tci": ["tcichemicals.com", "tokyokasei.co.jp"],
    "santa cruz": ["scbt.com"],
    "cayman": ["caymanchem.com", "caymanchemical.com"],
    "bio rad": ["bio-rad.com", "biorad.com"],
    "promega": ["promega.com"],
    "promega corporation": ["promega.com"],
    "abcam": ["abcam.com"],
    "cell signaling technology": ["cellsignal.com"],
    "cell signaling": ["cellsignal.com"],
    "cst": ["cellsignal.com"],
    "new england biolabs": ["neb.com"],
    "neb": ["neb.com"],
    "ecolab": ["ecolab.com", "safetydata.ecolab.com"],
    "3m": ["3m.com", "multimedia.3m.com"],
    "dow": ["dow.com", "dowcorning.com"],
    "basf": ["basf.com", "basf.us"],
    "dupont": ["dupont.com"],
    "eastman": ["eastman.com"],
    "evonik": ["evonik.com"],
    "airgas": ["airgas.com"],
    "linde": ["linde.com", "linde-gas.com", "praxair.com"],
    "matheson": ["mathesongas.com"],
    "bayer": ["bayer.com", "cropscience.bayer.com", "cropscience.bayer.us"],
    "bayer cropscience": ["cropscience.bayer.com", "bayer.com", "cropscience.bayer.us"],
    "air liquide": ["airliquide.com", "industry.airliquide.us"]
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
        "section_1_identification": r'(?:section\s*1[-:.]?\s*(?:identification|chemical product|product and company)|1\.\s*identification)',
        "section_2_hazards": r'(?:section\s*(?:2|3)[-:.]?\s*(?:hazard|hazards identification|composition)|2\.\s*hazard)',
        "section_3_composition": r'(?:section\s*(?:2|3)[-:.]?\s*(?:composition|ingredient)|3\.\s*composition)',
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

def is_pdf_content(raw_data: bytes, content_type: str = "", url: str = "") -> bool:
    """
    Deterministically validates whether raw document bytes and metadata represent a real PDF.
    Ensures a response is not considered a PDF solely due to URL extension or Content-Type header;
    requires valid %PDF magic-byte confirmation when raw data is available.
    """
    if not raw_data:
        ct = (content_type or "").lower()
        u = (url or "").lower().split("?")[0]
        return "application/pdf" in ct or u.endswith(".pdf")

    # Safe %PDF magic byte check within the initial 1024 bytes (ignoring leading whitespace/BOM)
    prefix = raw_data[:1024].lstrip()
    return prefix.startswith(b"%PDF")

is_pdf = is_pdf_content

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
    is_pdf_doc = is_pdf_content(raw_data, content_type, url)
    full_text = ""

    try:
        if is_pdf_doc:
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

    url_type = "pdf" if is_pdf_doc else "landing_page"
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
