# L2 SDS Intelligence — Independent Benchmark Evaluation Report

**Evaluation Run ID**: `eval_20260828_105300_327150`
**Execution Timestamp**: `2026-08-28T10:55:53.632719+00:00`
**Dataset**: `data/ground_truth.json` (15 Multi-Class Benchmark Cases)
**Evaluation Method**: Strict Non-Circular Ground Truth Comparison

---

## 1. Independent Correctness & Grounding Metrics

| Benchmark Metric | Score | Percentage |
|---|---|---|
| **Status Accuracy** | **11/15** | **73.3%** |
| **Exact Match Accuracy** | **2/5** | **40.0%** |
| **Best Available Accuracy** | **3/4** | **75.0%** |
| **Needs Review / Abstention Accuracy** | **6/6** | **100.0%** |
| **Product Verification Accuracy** | **11/15** | **73.3%** |
| **Manufacturer Verification Accuracy** | **11/15** | **73.3%** |
| **Country / Jurisdiction Accuracy** | **10/15** | **66.7%** |
| **Language Accuracy** | **11/15** | **73.3%** |
| **URL Grounding Accuracy** | **11/15** | **73.3%** |
| **Overall Case Accuracy** | **10/15** | **66.7%** |

---

## 2. Execution Latency Profile

* **Total Pipeline Latency**: 171.49 seconds
* **Average Latency per Request**: 11.11 seconds
* **Minimum Request Latency**: 0.01 seconds
* **Maximum Request Latency**: 27.76 seconds

---

## 3. Per-Item Independent Comparison Matrix

| Case ID | Category | Chemical Product | Expected Status | Actual Status | Product | Manufacturer | Country | Language | URL Grounded | Overall | Latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `GT_001` | `EXACT_MATCH` | **Acetone** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 27.76s |
| `GT_002` | `EXACT_MATCH` | **Isopropyl Alcohol** | `EXACT MATCH` | `EXACT MATCH` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 8.14s |
| `GT_003` | `EXACT_MATCH` | **Sulfuric Acid** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 14.06s |
| `GT_004` | `EXACT_MATCH` | **Methanol** | `EXACT MATCH` | `EXACT MATCH` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 7.99s |
| `GT_005` | `EXACT_MATCH` | **Toluene** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 9.91s |
| `GT_006` | `BEST_AVAILABLE` | **Hydrochloric Acid 37%** | `BEST AVAILABLE` | `BEST AVAILABLE` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 9.64s |
| `GT_007` | `BEST_AVAILABLE` | **Ethanol 200 Proof** | `BEST AVAILABLE` | `BEST AVAILABLE` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 10.98s |
| `GT_008` | `NEEDS_REVIEW` | ***[Empty Product]*** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 0.02s |
| `GT_009` | `WRONG_PRODUCT` | **Kryptonite Tetrafluoride Nonexistent Chemical** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 12.51s |
| `GT_010` | `WRONG_MANUFACTURER` | **Sodium Hydroxide** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 18.88s |
| `GT_011` | `WRONG_COUNTRY_JURISDICTION` | **Nitric Acid** | `BEST AVAILABLE` | `BEST AVAILABLE` | PASS | PASS | FAIL | PASS | GROUNDED | **FAIL** | 8.89s |
| `GT_012` | `WRONG_LANGUAGE` | **Benzene** | `BEST AVAILABLE` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 11.84s |
| `GT_013` | `NO_VALID_DOCUMENT` | **Unsynthesized Experimental Reagent X9999** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 11.71s |
| `GT_014` | `AMBIGUOUS_CASE` | **Generic Hydrocarbon Mixture Unspecified** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 14.25s |
| `GT_015` | `SECURITY_REJECTION` | **Acetone Localhost Attack Test** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 0.01s |

---

## 4. Evaluation Policy & Grounding Invariants

1. **Strict Status Separation**: `EXACT MATCH`, `BEST AVAILABLE`, and `NEEDS REVIEW` are strictly evaluated. No status collapsing or credit sharing.
2. **Independent Product & Manufacturer Verification**: Evaluator compares ground truth tokens against raw fetched documents and URLs directly rather than accepting internal model claims.
3. **Deterministic URL Grounding**: URLs must match ground truth `acceptable_domains` or `acceptable_urls`. Generic keyword matching is disallowed.
4. **Abstention Scoring**: Negative cases (`WRONG_PRODUCT`, `WRONG_MANUFACTURER`, `SECURITY_REJECTION`, etc.) require `NEEDS REVIEW` with an empty URL to pass.
