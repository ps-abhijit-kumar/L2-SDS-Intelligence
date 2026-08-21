import re
import urllib.request
import pymupdf as fitz  # PyMuPDF
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from ddgs import DDGS
import time

TRUSTED_SITES = [
    # --- Major Chemical & Lab Suppliers (Highest Coverage) ---
    "sigmaaldrich.com",
    "fishersci.com",
    "thermofisher.com",
    "vwr.com",
    "avantorsciences.com",
    "merckmillipore.com",
    "tcichemicals.com",
    "spectrumchemical.com",
    "scbt.com",                 # Santa Cruz Biotechnology
    "caymanchem.com",           # Cayman Chemical

    # --- Life Science & Reagent Vendors ---
    "bio-rad.com",
    "promega.com",
    "neb.com",                  # New England Biolabs
    "abcam.com",
    "cellsignal.com",           # Cell Signaling Technology

    # --- Industrial & Specialty Chemical Manufacturers ---
    "3m.com",
    "ecolab.com",
    "dow.com",
    "basf.com",
    "dupont.com",
    "eastman.com",
    "evonik.com",

    # --- Industrial Gas & Specialty Material Vendors ---
    "airgas.com",
    "linde.com",
    "mathesongas.com",

    # --- Institutional, Regulatory & Open Databases ---
    "cdc.gov/niosh",
    "echa.europa.eu",
    "pubchem.ncbi.nlm.nih.gov",  # Direct GHS / SDS data sections
    "ilpi.com",                 # Household Chemical / MSDS HyperGlossary & Links
    "msdssolutions.com",
]

@tool
def search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """
    Executes a web search using DuckDuckGo to find potential Safety Data Sheets.
    Use this to gather candidates. It returns deduplicated results containing URL and text snippet.
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
                            "snippet": res.get("body", "")
                        })
            time.sleep(0.5) # rate limiting
    except Exception as e:
        return [{"error": f"Search failed: {e}"}]
        
    return results

@tool
def rank_sds_candidates(candidates: list[dict], target_product: str, target_company: str) -> list[dict]:
    """
    Deterministically ranks search candidates based on heuristics.
    Pass in the list of search results, and the requested product and company name.
    Returns the same list, but sorted with the most likely candidates first, adding a 'score'.
    """
    target_product = target_product.lower()
    target_company = target_company.lower()
    company_cleaned = re.sub(r'[^a-z0-9]', '', target_company)
    
    ranked = []
    for cand in candidates:
        if "error" in cand:
            continue
            
        content = str(cand.get("snippet", "")).lower()
        url = str(cand.get("url", "")).lower()
        
        score = 0
        if target_product in url or target_product in content:
            score += 40
            
        if company_cleaned and company_cleaned in url:
            score += 30
        elif target_company and target_company in content:
            score += 15
            
        if ".pdf" in url:
            score += 20
            
        if "safety data sheet" in content or "sds" in url or "msds" in url:
            score += 10
            
        # Bonus for trusted sites
        if any(ts in url for ts in TRUSTED_SITES):
            score += 15
            
        ranked.append({
            "url": cand["url"],
            "score": score,
            "snippet": cand.get("snippet", "")
        })
        
    return sorted(ranked, key=lambda x: x["score"], reverse=True)

@tool
def fetch_document_text(url: str) -> str:
    """
    Fetches the content of a URL. If it's a PDF, extracts the text from the first page.
    If it's an HTML page, extracts the visible text. 
    Use this to get evidence from the document to verify product name, manufacturer, country, etc.
    """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get('Content-Type', '')
            data = response.read()
            
            if 'application/pdf' in content_type.lower() or url.lower().endswith('.pdf'):
                doc = fitz.open(stream=data, filetype="pdf")
                if len(doc) > 0:
                    page_text = doc[0].get_text()
                    return page_text[:800] # return first 800 chars of page 1
                return "PDF is empty."
            else:
                soup = BeautifulSoup(data, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                return text[:800] # return first 800 chars
    except Exception as e:
        return f"Error fetching document: {e}"
