# L2 SDS Intelligence — Reproducible Benchmark Evaluation Report

**Evaluation Run ID**: `eval_20260824_081349_299c37`
**Execution Timestamp**: `2026-08-24T08:16:03.164647+00:00`
**Dataset**: `data/ground_truth.json` (10 Benchmark Cases)
**LangGraph Architecture**: Dynamic Action Selection + Independent Reflection Verification Stage

---

## 1. Executive Performance & Correctness Metrics

| Benchmark Metric | Result | Target Benchmark | Status |
|---|---|---|---|
| **Status Classification Accuracy** | **60.0%** | >= 70.0% | REVIEW |
| **URL Grounding Correctness** | **60.0%** | >= 70.0% | REVIEW |
| **Manufacturer Verification Rate** | **60.0%** | >= 80.0% | REVIEW |
| **Product Specification Accuracy** | **60.0%** | >= 85.0% | REVIEW |
| **Composite Field-Level Accuracy** | **60.0%** | >= 75.0% | REVIEW |
| **Automated Resolution Rate** | **60.0%** | >= 60.0% | PASS |

---

## 2. Execution Latency Profile

* **Total Pipeline Latency**: 133.40 seconds
* **Average Latency per Request**: 13.03 seconds
* **Minimum Request Latency**: 3.39 seconds
* **Maximum Request Latency**: 29.24 seconds

---

## 3. Verdict Distribution Breakdown

* **Exact Matches (`EXACT MATCH`)**: 2 (20.0%)
* **Best Available (`BEST AVAILABLE`)**: 4 (40.0%)
* **Human Review Flagged (`NEEDS REVIEW`)**: 4 (40.0%)
* **Pipeline Errors (`ERROR`)**: 0 (0.0%)

---

## 4. Per-Item Ground Truth Comparison Matrix

| Case ID | Chemical Product | Target Manufacturer | Expected Status | Verified Status | URL Grounding | Confidence | Latency |
|---|---|---|---|---|---|---|---|
| `GT_001` | **Acetone** | Sigma-Aldrich | `EXACT MATCH` | `BEST AVAILABLE` | `PASS` | 70% | 26.89s |
| `GT_002` | **Isopropyl Alcohol** | Fisher Scientific | `EXACT MATCH` | `BEST AVAILABLE` | `PASS` | 70% | 6.51s |
| `GT_003` | **Sulfuric Acid** | Merck | `EXACT MATCH` | `NEEDS REVIEW` | `N/A` | 0% | 3.66s |
| `GT_004` | **Methanol** | Thermo Fisher | `EXACT MATCH` | `EXACT MATCH` | `PASS` | 85% | 4.43s |
| `GT_005` | **Toluene** | Honeywell | `EXACT MATCH` | `EXACT MATCH` | `PASS` | 85% | 13.03s |
| `GT_006` | **Benzene** | Sigma-Aldrich | `EXACT MATCH` | `NEEDS REVIEW` | `N/A` | 0% | 28.06s |
| `GT_007` | **Hydrochloric Acid** | Fisher Scientific | `EXACT MATCH` | `NEEDS REVIEW` | `N/A` | 50% | 7.96s |
| `GT_008` | **Ethanol** | Merck | `EXACT MATCH` | `NEEDS REVIEW` | `N/A` | 0% | 3.39s |
| `GT_009` | **Nitric Acid** | Thermo Fisher | `EXACT MATCH` | `BEST AVAILABLE` | `PASS` | 70% | 7.17s |
| `GT_010` | **Sodium Hydroxide** | Sigma-Aldrich | `EXACT MATCH` | `BEST AVAILABLE` | `PASS` | 70% | 29.24s |

---

## 5. Architectural Safeguards Verified

1. **Independent Reflection & Verification**: Every candidate passes through the programmatic and semantic verification node before final verdict generation.
2. **Strict Grounding Invariant**: Zero hallucinated URLs accepted; all final URLs strictly verified against discovered search candidates and fetched payloads.
3. **SSRF & Network Safety**: All document fetching routes are protected with DNS IP validation, blocked private CIDR checks, redirect re-validation, and 10MB chunked stream limits.
4. **Strict Pydantic Validation**: All outputs strictly conform to `SDSValidationResult` bounds (`0 <= confidence <= 100`, bounded status literals).
