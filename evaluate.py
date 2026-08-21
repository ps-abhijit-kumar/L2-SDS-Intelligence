import os
import sys
import subprocess
import time
import pandas as pd

def run_evaluation():
    print("Starting automated evaluation over test rows...")
    
    # The MCP server is available in src/mcp_server.py.
    
    start_time = time.time()
    try:
        # Run main pipeline
        subprocess.run([sys.executable, "main.py"], check=True)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        return
        
    duration = time.time() - start_time
    
    # Evaluate results
    df = pd.read_excel("sample_requests_eval.xlsx")
    total = len(df)
    exact_matches = len(df[df["Status"] == "EXACT MATCH"])
    needs_review = len(df[df["Status"] == "NEEDS REVIEW"])
    best_available = len(df[df["Status"] == "BEST AVAILABLE"])
    errors_or_empty = total - (exact_matches + needs_review + best_available)
    
    report = f"""# Automated Evaluation Report
    
- **Total Requests Processed**: {total}
- **Total Pipeline Latency**: {duration:.2f} seconds
- **Average Latency per Request**: {(duration/total):.2f} seconds

### Results Breakdown:
- **Exact Matches Found**: {exact_matches}
- **Best Available Found**: {best_available}
- **Flagged for Human Review**: {needs_review}
- **Errors/Empty**: {errors_or_empty}

### Performance Analysis:
Success Rate (Automated Resolution): {((exact_matches + best_available) / total) * 100:.2f}%
Human Intervention/Error Rate: {((needs_review + errors_or_empty) / total) * 100:.2f}%
"""
    
    with open("evaluation_report.md", "w") as f:
        f.write(report)
        
    print("\nEvaluation Complete! See evaluation_report.md")

if __name__ == "__main__":
    run_evaluation()
