import asyncio
from src.evaluation import run_evaluation_suite

def main():
    asyncio.run(run_evaluation_suite())
    print("\nEvaluation complete. Full report regenerated in evaluation_report.md.")

if __name__ == "__main__":
    main()
