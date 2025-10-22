# src/judge/text_only_utils.py
"""
Utilities used by the VPP Judge:
- structural_checks(vpp_text)
- judge_closeness_multi(candidate_text, gt_text)
- judge_pairwise_multi(candA_text, candB_text, gt_text, labelA, labelB)

This module depends on:
  - databricks-langchain
  - langchain-core
"""

from __future__ import annotations
from typing import Dict, Any, Tuple, List
import json, re, time

# from databricks_langchain import ChatDatabricks   # <-- remove
from langchain_community.chat_models import ChatDatabricks
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# =========================
# Basic helpers / constants
# =========================

def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def _clamp_len(s: str | None, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"

JUDGE_MAX_TOKENS = 2500

# Candidate judge endpoints to try (order matters). Adjust as needed for your workspace.
JUDGE_ENDPOINTS: List[str] = [
    "databricks-claude-3-7-sonnet",
    "databricks-claude-sonnet-4",
    "databricks-meta-llama-3-3-70b-instruct",
]

def get_judge(endpoint: str):
    return ChatDatabricks(endpoint=endpoint, temperature=0.0, max_tokens=JUDGE_MAX_TOKENS)

def _validate_endpoint(endpoint: str) -> bool:
    try:
        model = ChatDatabricks(endpoint=endpoint, temperature=0.0, max_tokens=8)
        out = model.invoke("ping")
        return bool(getattr(out, "content", "ok"))
    except Exception:
        return False

# Build a validated list once on import.
_VALID_JUDGES: List[str] = [e for e in JUDGE_ENDPOINTS if _validate_endpoint(e)]
if not _VALID_JUDGES:
    # last-ditch fallback; if this also doesn't exist in your workspace, replace it
    _VALID_JUDGES = ["databricks-claude-3-7-sonnet"]


# =========================
# Structural checks (text)
# =========================

BRIEF_PAT = r"(?i)\b(Brief\s+One[- ]Liner|One[- ]Liner|Brief\s+Summary|Summary\s*—?\s*One[- ]Liner|Brief\s+Synopsis)\b"
HIST_PAT  = r"(?i)\b(Oncologic\s+History|Oncology\s+History|Cancer\s+History|Oncologic\s+Timeline|Treatment\s+History)\b"

def structural_checks(vpp: str) -> Dict[str, int]:
    s = vpp or ""
    has_brief = 1 if re.search(BRIEF_PAT, s) else 0
    has_hist  = 1 if re.search(HIST_PAT, s) else 0
    mmddyyyy  = 1 if re.search(r"\b\d{2}/\d{2}/\d{4}\b", s) else 0
    try:
        brief_m = re.search(BRIEF_PAT, s)
        hist_m  = re.search(HIST_PAT, s)
        brief_pos = brief_m.start() if brief_m else -1
        hist_pos  = hist_m.start() if hist_m else 1<<30
        correct_order = 1 if (brief_pos == -1 or brief_pos < hist_pos) else 0
    except Exception:
        correct_order = 0
    return {
        "has_brief": has_brief,
        "has_history": has_hist,
        "correct_order": correct_order,
        "has_mmddyyyy": mmddyyyy,
    }


# =========================
# Closeness judge (to GT)
# =========================

CLOSE_SYS = SystemMessagePromptTemplate.from_template(
    "Score closeness (0.0–1.0) of the candidate VPP note to the ground-truth VPP text. "
    "Consider structure, key diagnoses, treatments, dates, and timeline accuracy. "
    "Return JSON ONLY with keys 'closeness' (float) and 'rationale' (string)."
)
CLOSE_HUM = HumanMessagePromptTemplate.from_template(
    "GROUND TRUTH VPP:\n{gt}\n\nCANDIDATE (VPP):\n{cand}\n\nRespond with strict JSON only."
)
CLOSE_PROMPT = ChatPromptTemplate.from_messages([CLOSE_SYS, CLOSE_HUM])

def _judge_closeness_one(candidate: str, gt_text: str, judge_endpoint: str) -> Tuple[float | None, str, float]:
    t0 = time.time()
    try:
        model = get_judge(judge_endpoint)
        out = (CLOSE_PROMPT | model).invoke({"gt": gt_text, "cand": candidate})
        raw = (out.content or "").strip()
        m = re.search(r"\{.*\}", raw, re.S)
        closeness, rationale = None, ""
        if m:
            obj = json.loads(m.group(0))
            closeness = _safe_float(obj.get("closeness"))
            rationale = obj.get("rationale", "")
    except Exception as e:
        closeness, rationale = None, f"judge error: {str(e)[:200]}"
    return closeness, rationale, time.time() - t0

def judge_closeness_multi(candidate: str, gt_text: str) -> Dict[str, Any]:
    per_judge = []
    vals: List[float] = []
    total_sec = 0.0
    for je in _VALID_JUDGES:
        c, r, sec = _judge_closeness_one(candidate, gt_text, je)
        total_sec += sec
        per_judge.append({
            "judge_endpoint": je,
            "closeness": c,
            "elapsed_sec": sec,
            "rationale": _clamp_len(r, 1000),
        })
        if c is not None:
            vals.append(float(c))
    agg = float(sum(vals)/len(vals)) if vals else None
    rationale = " | ".join([pj["rationale"] for pj in per_judge if pj.get("rationale")][:2])
    return {
        "closeness": agg,
        "rationale": _clamp_len(rationale, 2000),
        "elapsed_sec": total_sec,
        "n_judges": len(_VALID_JUDGES),
        "details": per_judge,
    }


# =========================
# Pairwise preference judge
# =========================

def _pref_sys_tmpl(labelA: str, labelB: str) -> SystemMessagePromptTemplate:
    return SystemMessagePromptTemplate.from_template(
        "You are a strict clinical documentation judge. Compare two VPP candidates against the ground-truth VPP text. "
        "Decide which candidate is closer to ground-truth AND better formatted as a VPP note. "
        f"Return JSON ONLY with keys: preferred (must be '{labelA}' or '{labelB}' or 'tie'), "
        f"scores (object with '{labelA}' and '{labelB}' integer 0-100), "
        f"vpp_compliance_estimate (object with '{labelA}' and '{labelB}' floats 0-1), explanation."
    )

PREF_HUM = HumanMessagePromptTemplate.from_template(
    "GROUND TRUTH VPP:\n{gt}\n\n{labelA}:\n{candA}\n\n{labelB}:\n{candB}\n\nRespond with strict JSON only."
)

def _judge_pairwise_one(candA: str, candB: str, gt_text: str, labelA: str, labelB: str, judge_endpoint: str):
    t0 = time.time()
    try:
        SYS = _pref_sys_tmpl(labelA, labelB)
        PROMPT = ChatPromptTemplate.from_messages([SYS, PREF_HUM])
        model = get_judge(judge_endpoint)
        out = (PROMPT | model).invoke({"gt": gt_text, "candA": candA, "candB": candB, "labelA": labelA, "labelB": labelB})
        raw = (out.content or "").strip()
        m = re.search(r"\{.*\}", raw, re.S)
        res = {"preferred": None, "scores": {labelA: None, labelB: None},
               "vpp_compliance_estimate": {labelA: None, labelB: None}, "explanation": ""}
        if m:
            obj = json.loads(m.group(0))
            res.update(obj)
    except Exception as e:
        res = {"preferred": None, "scores": {labelA: None, labelB: None},
               "vpp_compliance_estimate": {labelA: None, labelB: None},
               "explanation": f"judge error: {str(e)[:200]}"}
    return res, time.time() - t0

def judge_pairwise_multi(candA: str, candB: str, gt_text: str, labelA: str, labelB: str) -> Dict[str, Any]:
    votes = {labelA: 0, labelB: 0, "tie": 0}
    scoresA: List[float] = []
    scoresB: List[float] = []
    compA: List[float] = []
    compB: List[float] = []
    details = []
    total_sec = 0.0

    for je in _VALID_JUDGES:
        r, sec = _judge_pairwise_one(candA, candB, gt_text, labelA, labelB, je)
        total_sec += sec
        details.append({"judge_endpoint": je, "result": r, "elapsed_sec": sec})
        pref = r.get("preferred")
        if pref == labelA:
            votes[labelA] += 1
        elif pref == labelB:
            votes[labelB] += 1
        else:
            votes["tie"] += 1

        a = _safe_float((r.get("scores", {}) or {}).get(labelA))
        b = _safe_float((r.get("scores", {}) or {}).get(labelB))
        if a is not None: scoresA.append(a)
        if b is not None: scoresB.append(b)

        ca = _safe_float((r.get("vpp_compliance_estimate", {}) or {}).get(labelA))
        cb = _safe_float((r.get("vpp_compliance_estimate", {}) or {}).get(labelB))
        if ca is not None: compA.append(ca)
        if cb is not None: compB.append(cb)

    # Majority vote (ties allowed)
    preferred = None
    if votes[labelA] > votes[labelB]:
        preferred = labelA
    elif votes[labelB] > votes[labelA]:
        preferred = labelB
    else:
        preferred = "tie"

    return {
        "preferred": preferred,
        "scoreA": float(sum(scoresA) / len(scoresA)) if scoresA else None,
        "scoreB": float(sum(scoresB) / len(scoresB)) if scoresB else None,
        "compA": float(sum(compA) / len(compA)) if compA else None,
        "compB": float(sum(compB) / len(compB)) if compB else None,
        "elapsed_sec": total_sec,
        "n_judges": len(_VALID_JUDGES),
        "details": details,
    }
