import os
import re
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Literal

import dotenv
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq

from src.state import SDSState
from src.schema import (
    SDSValidationResult,
    VerificationResult,
    ActionDecision,
    SDSEvidence,
    ValidStatus,
    ActionType,
    is_valid_http_url
)
from src.tools import search_duckduckgo, rank_sds_candidates, fetch_document_text
from src.security import safe_fetch_document, SecurityError
from src.sds_parser import (
    parse_sds_document,
    normalize_identifier,
    normalize_text,
    normalize_url
)

dotenv.load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

def get_llm():
    if groq_api_key and groq_api_key != "your_groq_api_key_here":
        try:
            return ChatGroq(
                temperature=0,
                groq_api_key=groq_api_key,
                model_name=groq_model
            )
        except Exception:
            return None
    return None

# ==============================================================================
# Helper Verification Logic (Independently Testable Verification Core)
# ==============================================================================

def perform_verification(
    row_data: Dict[str, Any],
    draft_status: str,
    draft_url: str,
    draft_confidence: int,
    draft_reasoning: str,
    discovered_candidates: List[Dict[str, Any]],
    successful_fetches: Dict[str, Dict[str, Any]],
    failed_fetches: Dict[str, str]
) -> VerificationResult:
    """
    Independent, deterministic & programmatic verification engine.
    Cross-checks the draft decision against ground truth request parameters,
    discovered candidate URLs, and raw fetched document evidence.
    """
    row_data = row_data or {}
    discovered_candidates = discovered_candidates or []
    successful_fetches = successful_fetches or {}
    failed_fetches = failed_fetches or {}

    req_product = str(row_data.get("Product Name") or row_data.get("Product") or "").strip()
    req_company = str(row_data.get("Product Company Name") or row_data.get("Company") or "").strip()
    req_part_number = str(row_data.get("Part Number") or "").strip()
    req_country = str(row_data.get("Country") or "").strip()
    req_language = str(row_data.get("Language") or "English").strip()

    norm_req_prod = normalize_text(req_product)
    norm_req_comp = normalize_text(req_company)
    norm_req_part = normalize_identifier(req_part_number)

    issues: List[str] = []
    corrections: Dict[str, Any] = {}

    clean_draft_url = draft_url.strip() if draft_url else ""
    norm_draft_url = normalize_url(clean_draft_url)

    # 1. Provenance & Grounding Verification (Priority 4)
    discovered_urls = {normalize_url(c.get("url", "")) for c in discovered_candidates if c.get("url")}

    if clean_draft_url:
        is_discovered = norm_draft_url in discovered_urls
        fetched_evidence_dict = None
        for fetched_url_key, ev in successful_fetches.items():
            if normalize_url(fetched_url_key) == norm_draft_url:
                fetched_evidence_dict = ev
                break

        if not is_discovered:
            issues.append(f"Grounding Failure: Selected URL '{clean_draft_url}' was not discovered in search results.")

        if not fetched_evidence_dict:
            issues.append(f"Grounding Failure: Selected URL '{clean_draft_url}' was not successfully fetched and verified.")
    else:
        fetched_evidence_dict = None

    if draft_status in ["EXACT MATCH", "BEST AVAILABLE"]:
        if not clean_draft_url:
            issues.append("Invalid State: Positive verdict with empty URL.")
            corrections["final_status"] = "NEEDS REVIEW"
            corrections["final_url"] = ""
            corrections["confidence"] = 0

        elif issues:
            corrections["final_status"] = "NEEDS REVIEW"
            corrections["final_url"] = ""
            corrections["confidence"] = min(30, draft_confidence)

    # 2. Document Content & Evidence Verification (Priority 6)
    product_match = False
    manufacturer_match = False
    part_number_match = None
    jurisdiction_match = None

    if fetched_evidence_dict and draft_status in ["EXACT MATCH", "BEST AVAILABLE"]:
        if isinstance(fetched_evidence_dict, dict):
            dict_copy = dict(fetched_evidence_dict)
            if "url" not in dict_copy:
                dict_copy["url"] = clean_draft_url
            evidence = SDSEvidence(**dict_copy)
        else:
            evidence = fetched_evidence_dict

        if not evidence.is_sds:
            issues.append("Document Authenticity Issue: Document lacks standard GHS/OSHA SDS headers.")
            corrections["final_status"] = "NEEDS REVIEW"
            corrections["final_url"] = ""
            corrections["confidence"] = min(20, draft_confidence)

        evidence_snippet = (evidence.raw_snippet + " " + " ".join(evidence.sections.values())).lower()
        prod_tokens = norm_req_prod.split()
        if prod_tokens:
            matching_tokens = sum(1 for tok in prod_tokens if tok in evidence_snippet or tok in clean_draft_url.lower())
            if matching_tokens / len(prod_tokens) >= 0.4:
                product_match = True
            else:
                issues.append(f"Product Mismatch: Evidence does not sufficiently reference '{req_product}'.")

        comp_clean = re.sub(r'[^a-z0-9]', '', norm_req_comp)
        if comp_clean and (comp_clean in clean_draft_url.lower() or comp_clean in evidence_snippet):
            manufacturer_match = True
        elif not norm_req_comp:
            manufacturer_match = True
        else:
            issues.append(f"Manufacturer Mismatch: Evidence does not confirm manufacturer '{req_company}'.")

        if norm_req_part:
            found_parts_norm = [normalize_identifier(p) for p in evidence.part_numbers]
            if norm_req_part in found_parts_norm or norm_req_part in normalize_identifier(evidence_snippet):
                part_number_match = True
            else:
                part_number_match = False
                issues.append(f"Part Number Discrepancy: Part number '{req_part_number}' not verified in document.")

        if req_country:
            if evidence.country and evidence.country.lower() in req_country.lower():
                jurisdiction_match = True
            else:
                jurisdiction_match = False

    # 3. Status & Confidence Adjustment / Downgrading Logic
    final_status: ValidStatus = draft_status if draft_status in ["EXACT MATCH", "BEST AVAILABLE", "NEEDS REVIEW"] else "NEEDS REVIEW"
    final_url: str = clean_draft_url
    confidence: int = max(0, min(100, draft_confidence))

    if "final_status" in corrections:
        final_status = corrections["final_status"]
    if "final_url" in corrections:
        final_url = corrections["final_url"]
    if "confidence" in corrections:
        confidence = corrections["confidence"]

    # Check if candidate is direct PDF vs landing page
    is_pdf = clean_draft_url.lower().split('?')[0].endswith('.pdf') or (fetched_evidence_dict and isinstance(fetched_evidence_dict, dict) and fetched_evidence_dict.get("url_type") == "pdf")
    url_type = "pdf" if is_pdf else "landing_page"

    if not is_pdf and clean_draft_url:
        # Landing page rule (Requirement 4 & 5): A landing page itself must NOT be treated as equivalent to retrieving the SDS PDF
        if final_status == "EXACT MATCH":
            final_status = "BEST AVAILABLE"
            confidence = min(70, confidence)
            issues.append("Document is an SDS Landing/Download Page rather than direct PDF. Direct PDF requires manual download.")

    if final_status == "EXACT MATCH":
        if not product_match or not manufacturer_match:
            if product_match and not manufacturer_match:
                final_status = "BEST AVAILABLE"
                confidence = min(75, confidence)
                issues.append("Downgraded EXACT MATCH -> BEST AVAILABLE due to unconfirmed manufacturer.")
            else:
                final_status = "NEEDS REVIEW"
                final_url = ""
                confidence = min(40, confidence)
                issues.append("Downgraded EXACT MATCH -> NEEDS REVIEW due to product/evidence mismatch.")

    if final_status == "EXACT MATCH" and confidence < 50:
        final_status = "NEEDS REVIEW"
        issues.append("Downgraded EXACT MATCH -> NEEDS REVIEW due to confidence < 50.")

    if final_status == "NEEDS REVIEW" and not product_match:
        final_url = ""

    reasoning_parts = []
    if final_status == "EXACT MATCH":
        reasoning_parts.append(f"Verified EXACT MATCH for '{req_product}' from {req_company or 'manufacturer'}.")
        if part_number_match:
            reasoning_parts.append(f"Part number {req_part_number} confirmed.")
        reasoning_parts.append("Direct SDS PDF document validated with authentic GHS safety sections.")
    elif final_status == "BEST AVAILABLE":
        if url_type == "landing_page":
            reasoning_parts.append(f"Legitimate SDS landing/download page retrieved for '{req_product}'. Direct PDF can be downloaded from manufacturer portal.")
        else:
            reasoning_parts.append(f"BEST AVAILABLE SDS retrieved for '{req_product}'.")
        if not manufacturer_match and req_company:
            reasoning_parts.append(f"Note: Candidate provides chemical specification but manufacturer '{req_company}' could not be definitively confirmed.")
        else:
            reasoning_parts.append("Matches chemical profile with minor jurisdiction or variant differences.")
    else:
        reasoning_parts.append("Flagged for human compliance review (NEEDS REVIEW).")
        if issues:
            reasoning_parts.append(f"Reason: {'; '.join(issues[:2])}.")
        else:
            reasoning_parts.append("No conclusive safety data sheet meeting exact compliance standards was found.")

    final_reasoning = " ".join(reasoning_parts)
    if len(final_reasoning) < 5:
        final_reasoning = "Document verification completed according to compliance requirements."

    approved = len(issues) == 0 and final_status == draft_status and final_url == draft_url

    return VerificationResult(
        approved=approved,
        issues=issues,
        corrections=corrections,
        evidence_sufficient=bool(fetched_evidence_dict or final_status == "NEEDS REVIEW"),
        final_status=final_status,
        final_url=final_url,
        url_type=url_type if final_url else None,
        confidence=confidence,
        reasoning=final_reasoning,
        product_match=product_match,
        manufacturer_match=manufacturer_match,
        part_number_match=part_number_match,
        jurisdiction_match=jurisdiction_match,
        required_additional_evidence=["section_1_identification"] if not product_match and final_status != "NEEDS REVIEW" else []
    )

# ==============================================================================
# Graph Nodes
# ==============================================================================

def decide_action_node(state: SDSState) -> Dict[str, Any]:
    """
    Dynamic Action Policy Engine (Priority 3).
    Evaluates current state, available candidates, fetched evidence, and action history
    to choose the next valid discrete action (SEARCH, RANK, FETCH, VERIFY, FINISH, RETRY).
    """
    iteration = state.get("iteration_count", 0) + 1
    retry_count = state.get("retry_count", 0)
    discovered = state.get("discovered_candidates") or []
    ranked = state.get("ranked_candidates") or []
    fetched_urls = state.get("fetched_urls") or []
    successful = state.get("successful_fetches") or {}
    failed = state.get("failed_fetches") or {}
    action_history = list(state.get("action_history") or [])
    draft = state.get("draft_decision")
    verification = state.get("verification_result")

    if iteration > 6:
        action_entry = {"action": "FINISH", "reason": "Iteration limit reached. Concluding retrieval.", "timestamp": datetime.now(timezone.utc).isoformat()}
        return {
            "next_action": "FINISH",
            "iteration_count": iteration,
            "action_history": action_history + [action_entry]
        }

    # 1. If no search candidates discovered yet -> SEARCH
    if not discovered:
        action_entry = {"action": "SEARCH", "reason": "Initial state: initiating targeted chemical discovery search.", "timestamp": datetime.now(timezone.utc).isoformat()}
        return {
            "next_action": "SEARCH",
            "iteration_count": iteration,
            "action_history": action_history + [action_entry]
        }

    # 2. If candidates discovered but unranked -> RANK
    if discovered and not ranked:
        action_entry = {"action": "RANK", "reason": "Candidates discovered: evaluating deterministic utility ranking.", "timestamp": datetime.now(timezone.utc).isoformat()}
        return {
            "next_action": "RANK",
            "iteration_count": iteration,
            "action_history": action_history + [action_entry]
        }

    unvisited = [c for c in ranked if c.get("url") and c.get("url") not in fetched_urls]

    # 3. If nothing successfully fetched yet, and unvisited candidates remain (up to 3 tries) -> FETCH
    if (not successful or not draft) and unvisited and len(fetched_urls) < 3 and not verification:
        top_cand = unvisited[0]
        action_entry = {
            "action": "FETCH",
            "target_url": top_cand.get("url"),
            "reason": f"Fetching candidate URL: {top_cand.get('url')}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return {
            "next_action": "FETCH",
            "current_candidate_url": top_cand.get("url", ""),
            "iteration_count": iteration,
            "action_history": action_history + [action_entry]
        }

    # 4. If fetch attempts made and no draft yet -> DRAFT
    if fetched_urls and not draft and not verification:
        action_entry = {"action": "DRAFT", "reason": "Gathered candidate evidence: drafting compliance verdict.", "timestamp": datetime.now(timezone.utc).isoformat()}
        return {
            "next_action": "DRAFT",
            "iteration_count": iteration,
            "action_history": action_history + [action_entry]
        }

    # 5. If draft formulated and not verified -> VERIFY
    if draft and not verification:
        action_entry = {"action": "VERIFY", "reason": "Draft formulated: executing independent verification stage.", "timestamp": datetime.now(timezone.utc).isoformat()}
        return {
            "next_action": "VERIFY",
            "iteration_count": iteration,
            "action_history": action_history + [action_entry]
        }

    # 6. Verification completed -> decide retry or finish
    if verification:
        if not verification.get("approved") and retry_count < 2 and unvisited:
            next_cand = unvisited[0]
            action_entry = {
                "action": "RETRY",
                "target_url": next_cand.get("url"),
                "reason": f"Verification requested alternative candidate: retrying with {next_cand.get('url')}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return {
                "next_action": "FETCH",
                "current_candidate_url": next_cand.get("url", ""),
                "retry_count": retry_count + 1,
                "draft_decision": None,
                "verification_result": None,
                "iteration_count": iteration,
                "action_history": action_history + [action_entry]
            }
        else:
            action_entry = {"action": "FINISH", "reason": "Verification completed. Concluding verdict.", "timestamp": datetime.now(timezone.utc).isoformat()}
            return {
                "next_action": "FINISH",
                "iteration_count": iteration,
                "action_history": action_history + [action_entry]
            }

    action_entry = {"action": "FINISH", "reason": "Default completion.", "timestamp": datetime.now(timezone.utc).isoformat()}
    return {
        "next_action": "FINISH",
        "iteration_count": iteration,
        "action_history": action_history + [action_entry]
    }

def search_node(state: SDSState) -> Dict[str, Any]:
    row = state.get("row_data") or {}
    prod = str(row.get("Product Name") or row.get("Product") or "").strip()
    company = str(row.get("Product Company Name") or row.get("Company") or "").strip()
    language = str(row.get("Language") or "").strip()
    country = str(row.get("Country") or "").strip()

    # Guard: If any required SDS identity field is missing, flag as NEEDS REVIEW without fabricating defaults
    if not prod or not company or not language or not country:
        missing_fields = []
        if not prod:
            missing_fields.append("Product Name")
        if not company:
            missing_fields.append("Manufacturer")
        if not language:
            missing_fields.append("Language")
        if not country:
            missing_fields.append("Country/Jurisdiction")
        return {
            "discovered_candidates": [],
            "final_status": "NEEDS REVIEW",
            "final_url": "",
            "confidence": 0,
            "detailed_reasoning": f"Incomplete SDS search identity: missing required field(s): {', '.join(missing_fields)}. Cannot execute verified retrieval without complete request parameters.",
            "next_action": "FINISH",
            "messages": [
                HumanMessage(content=f"Search halted: missing required SDS identity fields ({', '.join(missing_fields)}). Marked as NEEDS REVIEW.")
            ]
        }

    # Primary search identity uses ONLY the four required fields:
    # 1. Product Name, 2. Manufacturer Company, 3. SDS Language, 4. Jurisdiction/Country
    query_parts = []
    if prod:
        query_parts.append(f'"{prod}"' if " " in prod else prod)
    if company:
        query_parts.append(f'"{company}"' if " " in company else company)
    if language:
        query_parts.append(language)
    if country:
        query_parts.append(country)
    query_parts.append("SDS PDF Safety Data Sheet")

    query = " ".join(query_parts)

    results = search_duckduckgo.invoke({"query": query, "max_results": 5})

    discovered = []
    now_str = datetime.now(timezone.utc).isoformat()
    if isinstance(results, list):
        for idx, item in enumerate(results):
            if isinstance(item, dict) and "url" in item:
                discovered.append({
                    "candidate_id": f"cand_{idx}",
                    "url": item["url"],
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "source_query": query,
                    "discovered_at": now_str
                })

    # Optional Fallback Search: If primary 4-field search yielded no candidates and a Part/Catalog/CAS number is available
    part_num = str(row.get("Part Number") or "").strip()
    if len(discovered) == 0 and part_num:
        fb_parts = []
        if prod:
            fb_parts.append(f'"{prod}"' if " " in prod else prod)
        if company:
            fb_parts.append(f'"{company}"' if " " in company else company)
        fb_parts.append(part_num)
        fb_parts.append("SDS PDF")
        fb_query = " ".join(fb_parts)
        fb_results = search_duckduckgo.invoke({"query": fb_query, "max_results": 5})
        if isinstance(fb_results, list):
            for idx, item in enumerate(fb_results):
                if isinstance(item, dict) and "url" in item:
                    discovered.append({
                        "candidate_id": f"cand_fb_{idx}",
                        "url": item["url"],
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "source_query": fb_query,
                        "discovered_at": now_str
                    })

    return {
        "discovered_candidates": discovered,
        "messages": [
            HumanMessage(content=f"Search executed with query: '{query}'. Found {len(discovered)} candidates.")
        ]
    }

def rank_node(state: SDSState) -> Dict[str, Any]:
    row = state.get("row_data") or {}
    discovered = state.get("discovered_candidates") or []
    prod = str(row.get("Product Name") or row.get("Product") or "").strip()
    company = str(row.get("Product Company Name") or row.get("Company") or "").strip()
    part_num = str(row.get("Part Number") or "").strip()
    country = str(row.get("Country") or "").strip()

    ranked = rank_sds_candidates.invoke({
        "candidates": discovered,
        "target_product": prod,
        "target_company": company,
        "target_part_number": part_num,
        "target_country": country
    })

    top_url = ranked[0]["url"] if ranked else ""

    return {
        "ranked_candidates": ranked,
        "current_candidate_url": top_url,
        "messages": [
            AIMessage(content=f"Ranked {len(ranked)} candidates. Top candidate: {top_url}")
        ]
    }

def fetch_node(state: SDSState) -> Dict[str, Any]:
    target_url = state.get("current_candidate_url") or ""
    fetched_urls = list(state.get("fetched_urls") or [])
    successful = dict(state.get("successful_fetches") or {})
    failed = dict(state.get("failed_fetches") or {})

    if not target_url:
        return {"messages": [AIMessage(content="No candidate URL available to fetch.")]}

    if target_url not in fetched_urls:
        fetched_urls.append(target_url)

    try:
        data, content_type, final_url = safe_fetch_document(target_url, timeout=12.0)
        evidence = parse_sds_document(data, content_type, final_url)

        if evidence.fetched_successfully:
            successful[target_url] = evidence.model_dump()
            return {
                "fetched_urls": fetched_urls,
                "successful_fetches": successful,
                "current_candidate_url": target_url,
                "messages": [
                    AIMessage(content=f"Successfully fetched document from {target_url}. Is SDS: {evidence.is_sds}, CAS: {evidence.cas_numbers}")
                ]
            }
        else:
            failed[target_url] = evidence.error or "Failed to parse document."
            return {
                "fetched_urls": fetched_urls,
                "failed_fetches": failed,
                "messages": [
                    AIMessage(content=f"Failed to parse document from {target_url}: {evidence.error}")
                ]
            }

    except SecurityError as sec_err:
        failed[target_url] = f"Security Error: {str(sec_err)}"
        return {
            "fetched_urls": fetched_urls,
            "failed_fetches": failed,
            "messages": [AIMessage(content=f"Security Error on {target_url}: {str(sec_err)}")]
        }
    except Exception as e:
        failed[target_url] = str(e)
        return {
            "fetched_urls": fetched_urls,
            "failed_fetches": failed,
            "messages": [AIMessage(content=f"Fetch error on {target_url}: {str(e)}")]
        }

def draft_decision_node(state: SDSState) -> Dict[str, Any]:
    row = state.get("row_data") or {}
    prod = str(row.get("Product Name") or row.get("Product") or "").strip()
    company = str(row.get("Product Company Name") or row.get("Company") or "").strip()
    part_num = str(row.get("Part Number") or "").strip()
    country = str(row.get("Country") or "").strip()

    successful = state.get("successful_fetches") or {}
    ranked = state.get("ranked_candidates") or []

    # Pick the best fetched candidate
    selected_url = ""
    evidence_dict = None
    cand_score = 50

    for cand in ranked:
        cand_url = cand.get("url", "")
        if cand_url in successful:
            selected_url = cand_url
            evidence_dict = successful[cand_url]
            cand_score = cand.get("score", 50)
            break

    if not evidence_dict and successful:
        selected_url, evidence_dict = next(iter(successful.items()))

    if not evidence_dict or not selected_url:
        draft = {
            "status": "NEEDS REVIEW",
            "confidence": 0,
            "detailed_reasoning": f"No valid document could be retrieved for '{prod}'.",
            "final_url": ""
        }
        return {"draft_decision": draft, "current_candidate_url": ""}

    evidence = SDSEvidence(**evidence_dict)
    full_evidence_text = (evidence.raw_snippet + " " + " ".join(evidence.sections.values())).lower()

    norm_prod = normalize_text(prod)
    norm_comp = normalize_text(company)

    prod_tokens = norm_prod.split()
    prod_match = norm_prod in full_evidence_text or norm_prod in selected_url.lower() or (prod_tokens and any(t in full_evidence_text for t in prod_tokens if len(t) > 3))
    comp_clean = re.sub(r'[^a-z0-9]', '', norm_comp)
    comp_match = comp_clean in selected_url.lower() or comp_clean in full_evidence_text if comp_clean else True

    if evidence.is_sds and prod_match and comp_match:
        status = "EXACT MATCH"
        confidence = max(85, min(98, cand_score))
        reasoning = f"Exact match confirmed for {prod} from {company or 'manufacturer'} with verified SDS safety sections."
    elif evidence.is_sds and prod_match:
        status = "BEST AVAILABLE"
        confidence = max(70, min(84, cand_score))
        reasoning = f"Best available match confirmed for chemical {prod}. Manufacturer specification requires human review."
    else:
        status = "NEEDS REVIEW"
        confidence = max(20, min(50, cand_score))
        reasoning = f"Document retrieved from {selected_url} does not conclusively match requested chemical '{prod}'."

    draft = {
        "status": status,
        "confidence": confidence,
        "detailed_reasoning": reasoning,
        "final_url": selected_url if status != "NEEDS REVIEW" else ""
    }

    return {
        "draft_decision": draft,
        "current_candidate_url": selected_url,
        "messages": [
            AIMessage(content=f"Formulated draft decision: Status={status}, Confidence={confidence}, URL={draft['final_url']}")
        ]
    }

def verify_decision_node(state: SDSState) -> Dict[str, Any]:
    row = state.get("row_data") or {}
    draft = state.get("draft_decision") or {}
    discovered = state.get("discovered_candidates") or []
    successful = state.get("successful_fetches") or {}
    failed = state.get("failed_fetches") or {}

    draft_status = draft.get("status", "NEEDS REVIEW")
    draft_url = draft.get("final_url", "")
    draft_conf = draft.get("confidence", 0)
    draft_reason = draft.get("detailed_reasoning", "No draft reasoning.")

    verification = perform_verification(
        row_data=row,
        draft_status=draft_status,
        draft_url=draft_url,
        draft_confidence=draft_conf,
        draft_reasoning=draft_reason,
        discovered_candidates=discovered,
        successful_fetches=successful,
        failed_fetches=failed
    )

    ver_dict = verification.model_dump()

    return {
        "verification_result": ver_dict,
        "messages": [
            AIMessage(
                content=f"Verification result: approved={verification.approved}, "
                        f"final_status={verification.final_status}, "
                        f"confidence={verification.confidence}, "
                        f"issues={verification.issues}"
            )
        ]
    }

def corrective_action_node(state: SDSState) -> Dict[str, Any]:
    verification = state.get("verification_result") or {}
    final_status = verification.get("final_status", "NEEDS REVIEW")
    final_url = verification.get("final_url", "")
    confidence = verification.get("confidence", 0)
    reasoning = verification.get("reasoning", "Verification adjusted verdict.")

    return {
        "draft_decision": {
            "status": final_status,
            "final_url": final_url,
            "confidence": confidence,
            "detailed_reasoning": reasoning
        }
    }

def extract_final_node(state: SDSState) -> Dict[str, Any]:
    verification = state.get("verification_result") or {}
    draft = state.get("draft_decision") or {}
    row = state.get("row_data") or {}
    discovered = state.get("discovered_candidates") or []
    successful = state.get("successful_fetches") or {}

    status_candidate = verification.get("final_status") or draft.get("status") or "NEEDS REVIEW"
    url_candidate = verification.get("final_url") or draft.get("final_url") or ""
    conf_candidate = verification.get("confidence") if verification.get("confidence") is not None else draft.get("confidence", 0)
    reason_candidate = verification.get("reasoning") or draft.get("detailed_reasoning") or "Verification complete."

    if status_candidate not in ["EXACT MATCH", "BEST AVAILABLE", "NEEDS REVIEW"]:
        status_candidate = "NEEDS REVIEW"

    try:
        conf_int = int(conf_candidate)
        conf_int = max(0, min(100, conf_int))
    except (ValueError, TypeError):
        conf_int = 0

    url_str = str(url_candidate).strip()
    if status_candidate == "EXACT MATCH":
        if not url_str or not is_valid_http_url(url_str) or conf_int < 50:
            status_candidate = "NEEDS REVIEW"
            url_str = ""
            conf_int = min(40, conf_int)
            reason_candidate += " (Downgraded: ungrounded or invalid URL)."
    elif status_candidate == "BEST AVAILABLE":
        if url_str and not is_valid_http_url(url_str):
            url_str = ""

    url_type_cand = verification.get("url_type") or ("pdf" if url_str.lower().split("?")[0].endswith(".pdf") else "landing_page")

    provenance = {
        "selected_url": url_str,
        "url_type": url_type_cand if url_str else None,
        "discovered_candidates_count": len(discovered),
        "successful_fetches_count": len(successful),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "action_sequence": [a.get("action") for a in (state.get("action_history") or [])]
    }

    try:
        val_result = SDSValidationResult(
            status=status_candidate,
            confidence=conf_int,
            detailed_reasoning=reason_candidate,
            final_url=url_str,
            url_type=url_type_cand if url_str else None,
            provenance=provenance
        )
        final_status = val_result.status
        confidence = val_result.confidence
        detailed_reasoning = val_result.detailed_reasoning
        final_url = val_result.final_url
        url_type = val_result.url_type
    except Exception as val_err:
        final_status = "NEEDS REVIEW"
        confidence = 0
        final_url = ""
        url_type = None
        detailed_reasoning = f"Output validation adjusted: {str(val_err)}"

    return {
        "final_status": final_status,
        "confidence": confidence,
        "detailed_reasoning": detailed_reasoning,
        "final_url": final_url,
        "url_type": url_type,
        "provenance": provenance
    }

# ==============================================================================
# Conditional Edges
# ==============================================================================

def route_action(state: SDSState) -> str:
    action = state.get("next_action", "FINISH")
    if action == "SEARCH":
        return "search"
    elif action == "RANK":
        return "rank"
    elif action == "FETCH":
        return "fetch"
    elif action == "DRAFT":
        return "draft"
    elif action == "VERIFY":
        return "verify"
    elif action == "FINISH":
        return "extract_final"
    return "extract_final"

def route_verification(state: SDSState) -> str:
    verification = state.get("verification_result") or {}
    if verification.get("approved"):
        return "extract_final"

    corrections = verification.get("corrections") or {}
    if corrections:
        return "correct"

    return "extract_final"

# ==============================================================================
# Graph Construction
# ==============================================================================

def create_sds_graph():
    workflow = StateGraph(SDSState)

    workflow.add_node("decide_action", decide_action_node)
    workflow.add_node("search", search_node)
    workflow.add_node("rank", rank_node)
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("draft", draft_decision_node)
    workflow.add_node("verify", verify_decision_node)
    workflow.add_node("correct", corrective_action_node)
    workflow.add_node("extract_final", extract_final_node)

    workflow.set_entry_point("decide_action")

    workflow.add_conditional_edges(
        "decide_action",
        route_action,
        {
            "search": "search",
            "rank": "rank",
            "fetch": "fetch",
            "draft": "draft",
            "verify": "verify",
            "extract_final": "extract_final"
        }
    )

    workflow.add_edge("search", "decide_action")
    workflow.add_edge("rank", "decide_action")
    workflow.add_edge("fetch", "decide_action")
    workflow.add_edge("draft", "verify")

    workflow.add_conditional_edges(
        "verify",
        route_verification,
        {
            "extract_final": "extract_final",
            "correct": "correct"
        }
    )

    workflow.add_edge("correct", "extract_final")
    workflow.add_edge("extract_final", END)

    return workflow.compile()
