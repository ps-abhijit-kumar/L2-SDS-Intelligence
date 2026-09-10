"""
Ground Truth Evaluation CLI Entry Point
=======================================
Architecture Role:
    Command-line interface to execute the automated benchmark evaluation suite
    against the curated chemical ground truth dataset (`data/ground_truth.json`).
    Regenerates accuracy, precision, recall, and grounding metrics in `evaluation_report.md`.
"""

import asyncio
from src.agent.evaluation import run_evaluation_suite

def main():
    asyncio.run(run_evaluation_suite())
    print("\nEvaluation complete. Full report regenerated in evaluation_report.md.")

if __name__ == "__main__":
    main()
