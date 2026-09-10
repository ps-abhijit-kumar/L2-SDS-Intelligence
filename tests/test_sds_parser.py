import pytest
from src.retrieval.sds_parser import (
    parse_sds_document,
    normalize_identifier,
    normalize_text,
    normalize_url,
    extract_sds_sections,
    is_chemical_name_match
)

def test_normalize_identifier():
    assert normalize_identifier("A416-4") == "a4164"
    assert normalize_identifier("179124-500ML") == "179124500ml"
    assert normalize_identifier("CAS 67-64-1") == "cas67641"
    assert normalize_identifier("") == ""

def test_normalize_url():
    assert normalize_url("https://www.sigmaaldrich.com/US/en/sds/sial/179124/") == "https://www.sigmaaldrich.com/US/en/sds/sial/179124"
    assert normalize_url("http://example.com:80/path") == "http://example.com/path"

def test_is_chemical_name_match():
    assert is_chemical_name_match("Ethanol 200 Proof", "Ethyl Alcohol Absolute 100%") is True
    assert is_chemical_name_match("Isopropyl Alcohol", "Safety Data Sheet for 2-Propanol") is True
    assert is_chemical_name_match("Hydrochloric Acid 37%", "Hydrochloric acid aqueous solution") is True
    assert is_chemical_name_match("Acetone", "Methanol SDS") is False

def test_extract_sds_sections():
    sample_text = """
    SECTION 1: Identification
    Product Name: Acetone
    Manufacturer: Sigma-Aldrich

    SECTION 2: Hazards Identification
    Flammable liquid Category 2

    SECTION 3: Composition / Information on Ingredients
    CAS-No. 67-64-1 Weight % >= 99

    SECTION 9: Physical and Chemical Properties
    Boiling point 56 C

    SECTION 15: Regulatory Information
    OSHA 29 CFR 1910.1200
    """
    sections = extract_sds_sections(sample_text)
    assert "section_1_identification" in sections
    assert "section_2_hazards" in sections
    assert "section_3_composition" in sections
    assert "section_15_regulatory" in sections
    assert "Acetone" in sections["section_1_identification"]
    assert "67-64-1" in sections["section_3_composition"]

def test_parse_sds_document_html():
    html_bytes = b"""
    <html>
      <head><title>Safety Data Sheet - Isopropyl Alcohol</title></head>
      <body>
        <h1>Safety Data Sheet</h1>
        <p>Section 1: Identification of the substance: Isopropyl Alcohol 99%</p>
        <p>Manufacturer: Fisher Scientific</p>
        <p>Catalog No: A416-4</p>
        <p>CAS Number: 67-63-0</p>
        <p>Revision Date: 01/15/2024</p>
        <p>OSHA 29 CFR 1910.1200 Hazard Communication</p>
      </body>
    </html>
    """
    ev = parse_sds_document(html_bytes, "text/html", "https://www.fishersci.com/sds/ipa.html")
    assert ev.fetched_successfully is True
    assert ev.is_sds is True
    assert "67-63-0" in ev.cas_numbers
    assert any("a416" in p.lower() for p in ev.part_numbers)
    assert ev.country == "United States"
    assert "Fisher" in ev.manufacturer
