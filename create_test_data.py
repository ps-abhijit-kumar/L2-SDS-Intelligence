"""
Synthetic Test Data Generation Utility
======================================
Architecture Role:
    Generates realistic chemical SDS test request records for local development,
    smoke tests, and spreadsheet batch processing demonstration (`sample_requests_eval.xlsx`).
"""

import pandas as pd
import random

def create_sample_excel():
    base_data = [
        ("Acetone", "Sigma-Aldrich", "United States", "English"),
        ("Isopropyl Alcohol", "Fisher Scientific", "Canada", "English"),
        ("Sulfuric Acid", "Merck", "United Kingdom", "English"),
        ("Methanol", "Thermo Fisher", "United States", "English"),
        ("Toluene", "Honeywell", "Germany", "English"),
        ("Benzene", "Sigma-Aldrich", "United States", "English"),
        ("Hydrochloric Acid", "Fisher Scientific", "United States", "English"),
        ("Ethanol", "Merck", "France", "English"),
        ("Nitric Acid", "Thermo Fisher", "Canada", "English"),
        ("Sodium Hydroxide", "Sigma-Aldrich", "United States", "English")
    ]
    
    data = []
    for i in range(10):
        product, company, country, lang = base_data[i % len(base_data)]
        
        # Slightly alter the names to make it realistic
        req_product = f"{product} {random.choice(['99%', 'Industrial Grade', 'Lab Grade', 'Solution'])}"
        
        data.append({
            "S.No.": i + 1,
            "Product": product,
            "Product Name": req_product,
            "Product Company Name": company,
            "Language": lang,
            "Country": country
        })
        
    df = pd.DataFrame(data)
    df.to_excel("sample_requests_eval.xlsx", index=False)
    print("Created sample_requests_eval.xlsx with 10 rows.")
    
    import os
    if os.path.exists("logs/agent_trace.jsonl"):
        os.remove("logs/agent_trace.jsonl")
        print("Cleared previous logs/agent_trace.jsonl for a fresh run.")

if __name__ == "__main__":
    create_sample_excel()
