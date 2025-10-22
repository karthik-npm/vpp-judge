# src/judge/backends.py
"""
Thin adapters around your existing evaluation functions.

Requires:
- src/vpp_evaluation.py with evaluate_row_with_unified_reporting(md_note, candidate_note)
- src/judge/text_only_utils.py with:
    structural_checks(vpp_text) -> dict
    judge_closeness_multi(candidate_text, gt_text) -> dict
    judge_pairwise_multi(candA_text, candB_text, gt_text, labelA, labelB) -> dict
"""

from typing import Dict, Any
import json

from helpers import evaluate_row_with_unified_reporting
from judge.text_only_utils import structural_checks, judge_closeness_multi, judge_pairwise_multi


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _truncate(s: str, n: int) -> str:
    if not s:
        return s
    return s if len(s) <= n else s[: n - 1] + "…"


def run_objective(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Objective judge: candidate vs ground-truth (closeness + structural checks).
    Expects payload['generated']['text'] and payload['ground_truth']['text'].
    """
    cand = payload["generated"]["text"]
    gt = payload["ground_truth"]["text"]

    close = judge_closeness_multi(cand, gt)  # {"closeness","rationale","n_judges","details",...}
    S = structural_checks(cand)

    return {
        "obj_closeness": _safe_float(close.get("closeness")),
        "obj_rationale": _truncate(close.get("rationale", ""), 2000),
        "obj_n_judges": int(close.get("n_judges", 0) or 0),
        "obj_details_json": _truncate(json.dumps(close.get("details", []), ensure_ascii=False), 6000),
        "obj_has_brief": int(S.get("has_brief", 0)),
        "obj_has_history": int(S.get("has_history", 0)),
        "obj_correct_order": int(S.get("correct_order", 0)),
        "obj_has_mmddyyyy": int(S.get("has_mmddyyyy", 0)),
    }


def run_subjective_pairwise(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Subjective pairwise judge: compare A vs B (optionally conditioned on GT for context).
    Expects payload['compare']['a']['text'] and ['compare']['b']['text'].
    """
    A = payload["compare"]["a"]["text"]
    B = payload["compare"]["b"]["text"]
    gt = payload.get("ground_truth", {}).get("text", "")  # optional context

    res = judge_pairwise_multi(A, B, gt, "A", "B")
    return {
        "subj_preferred": res.get("preferred"),
        "subj_score_a": _safe_float(res.get("scoreA")),
        "subj_score_b": _safe_float(res.get("scoreB")),
        "subj_vppcomp_a": _safe_float(res.get("compA")),
        "subj_vppcomp_b": _safe_float(res.get("compB")),
        "subj_n_judges": int(res.get("n_judges", 0) or 0),
        "subj_details_json": _truncate(json.dumps(res.get("details", []), ensure_ascii=False), 6000),
    }


def run_subjective_single(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Subjective single-note judge (your de-novo 7-step bundle + unified pass/fail).
    Uses context as the 'original MD note', and generated.text as the candidate.
    """
    ctx = payload.get("context", {}) or {}
    md = ctx.get("textract_text") or ctx.get("updates_text") or ""  # pick best available
    cand = payload["generated"]["text"]

    all_res = evaluate_row_with_unified_reporting(md, cand)

    vpp = all_res.get("VPPCompliance", {}) or {}
    uni = all_res.get("UnifiedPassFail", {}) or {}

    return {
        # Initial subjective rubric (may be present depending on your pipeline)
        "subj_relevance": (all_res.get("Relevance") or {}).get("Relevance"),
        "subj_coherence": (all_res.get("Coherence") or {}).get("Coherence"),
        "subj_completeness": (all_res.get("Completeness") or {}).get("Completeness"),
        "subj_correctness": (all_res.get("Correctness") or {}).get("Correctness"),
        # Final adjusted scores
        "subj_final_relevance": (all_res.get("FinalRelevance") or {}).get("FinalRelevance"),
        "subj_final_completeness": (all_res.get("FinalCompleteness") or {}).get("FinalCompleteness"),
        "subj_final_correctness": (all_res.get("FinalCorrectness") or {}).get("FinalCorrectness"),
        # VPP compliance + pass/fail
        "subj_vpp_level": vpp.get("VPPCompliance"),
        "subj_vpp_weighted": _safe_float(vpp.get("WeightedScore")),
        "subj_passfail": uni.get("PassFail"),
        "subj_overall_rating": uni.get("OverallRating"),
        # Raw bundle for deep debugging
        "subj_summary_json": _truncate(json.dumps(all_res, ensure_ascii=False), 15000),
    }
