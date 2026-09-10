import pytest
from src.excel.workbook_utils import (
    detect_column_mapping,
    classify_sheet,
    is_valid_product_value,
    COLUMN_SYNONYMS
)

def test_is_valid_product_value():
    assert is_valid_product_value("Acetone") is True
    assert is_valid_product_value("Isopropyl Alcohol 99%") is True
    assert is_valid_product_value("") is False
    assert is_valid_product_value("N/A") is False
    assert is_valid_product_value("Total") is False
    assert is_valid_product_value("Grand Total") is False

def test_detect_column_mapping_standard():
    cols = ["S.No.", "Product Product Name", "Product Company Name", "Part Numbers", "Language", "Country"]
    mapping = detect_column_mapping(cols)
    assert mapping["product"] == "Product Product Name"
    assert mapping["company"] == "Product Company Name"
    assert mapping["part_number"] == "Part Numbers"
    assert mapping["language"] == "Language"
    assert mapping["country"] == "Country"

def test_classify_sheet():
    assert classify_sheet("Part1", ["Product Name", "Manufacturer"], 20, 20) == "SDS_REQUESTS"
    assert classify_sheet("Allocation", ["Squad", "Member", "Count"], 0, 500) == "SUPPORTING_DATA"
    assert classify_sheet("Summary_Report", ["Metric", "Value"], 0, 10) == "SUMMARY"
