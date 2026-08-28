# L2 SDS Intelligence — Independent Benchmark Evaluation Report

**Evaluation Run ID**: `eval_20260828_085121_d99c85`
**Execution Timestamp**: `2026-08-28T08:56:11.788426+00:00`
**Dataset**: `data/ground_truth.json` (15 Multi-Class Benchmark Cases)
**Evaluation Method**: Strict Non-Circular Ground Truth Comparison

---

## 1. Independent Correctness & Grounding Metrics

| Benchmark Metric | Score | Percentage |
|---|---|---|
| **Status Accuracy** | **9/15** | **60.0%** |
| **Exact Match Accuracy** | **1/5** | **20.0%** |
| **Best Available Accuracy** | **2/4** | **50.0%** |
| **Needs Review / Abstention Accuracy** | **6/6** | **100.0%** |
| **Product Verification Accuracy** | **9/15** | **60.0%** |
| **Manufacturer Verification Accuracy** | **9/15** | **60.0%** |
| **Country / Jurisdiction Accuracy** | **8/15** | **53.3%** |
| **Language Accuracy** | **9/15** | **60.0%** |
| **URL Grounding Accuracy** | **9/15** | **60.0%** |
| **Overall Case Accuracy** | **8/15** | **53.3%** |

---

## 2. Execution Latency Profile

* **Total Pipeline Latency**: 290.49 seconds
* **Average Latency per Request**: 19.06 seconds
* **Minimum Request Latency**: 0.01 seconds
* **Maximum Request Latency**: 70.32 seconds

---

## 3. Per-Item Independent Comparison Matrix

| Case ID | Category | Chemical Product | Expected Status | Actual Status | Product | Manufacturer | Country | Language | URL Grounded | Overall | Latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `GT_001` | `EXACT_MATCH` | **Acetone** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 70.32s |
| `GT_002` | `EXACT_MATCH` | **Isopropyl Alcohol** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 28.43s |
| `GT_003` | `EXACT_MATCH` | **Sulfuric Acid** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 18.28s |
| `GT_004` | `EXACT_MATCH` | **Methanol** | `EXACT MATCH` | `EXACT MATCH` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 6.29s |
| `GT_005` | `EXACT_MATCH` | **Toluene** | `EXACT MATCH` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 11.35s |
| `GT_006` | `BEST_AVAILABLE` | **Hydrochloric Acid 37%** | `BEST AVAILABLE` | `BEST AVAILABLE` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 9.4s |
| `GT_007` | `BEST_AVAILABLE` | **Ethanol 200 Proof** | `BEST AVAILABLE` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 17.85s |
| `GT_008` | `NEEDS_REVIEW` | ***[Empty Product]*** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 0.01s |
| `GT_009` | `WRONG_PRODUCT` | **Kryptonite Tetrafluoride Nonexistent Chemical** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 18.94s |
| `GT_010` | `WRONG_MANUFACTURER` | **Sodium Hydroxide** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 11.85s |
| `GT_011` | `WRONG_COUNTRY_JURISDICTION` | **Nitric Acid** | `BEST AVAILABLE` | `BEST AVAILABLE` | PASS | PASS | FAIL | PASS | GROUNDED | **FAIL** | 6.07s |
| `GT_012` | `WRONG_LANGUAGE` | **Benzene** | `BEST AVAILABLE` | `NEEDS REVIEW` | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** | 7.55s |
| `GT_013` | `NO_VALID_DOCUMENT` | **Unsynthesized Experimental Reagent X9999** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 10.39s |
| `GT_014` | `AMBIGUOUS_CASE` | **Generic Hydrocarbon Mixture Unspecified** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 69.13s |
| `GT_015` | `SECURITY_REJECTION` | **Acetone Localhost Attack Test** | `NEEDS REVIEW` | `NEEDS REVIEW` | PASS | PASS | PASS | PASS | GROUNDED | **PASS** | 0.01s |

---

## 4. Evaluation Policy & Grounding Invariants

1. **Strict Status Separation**: `EXACT MATCH`, `BEST AVAILABLE`, and `NEEDS REVIEW` are strictly evaluated. No status collapsing or credit sharing.
2. **Independent Product & Manufacturer Verification**: Evaluator compares ground truth tokens against raw fetched documents and URLs directly rather than accepting internal model claims.
3. **Deterministic URL Grounding**: URLs must match ground truth `acceptable_domains` or `acceptable_urls`. Generic keyword matching is disallowed.
4. **Abstention Scoring**: Negative cases (`WRONG_PRODUCT`, `WRONG_MANUFACTURER`, `SECURITY_REJECTION`, etc.) require `NEEDS REVIEW` with an empty URL to pass.
