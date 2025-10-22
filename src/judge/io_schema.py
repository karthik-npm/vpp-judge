# src/judge/io_schema.py
"""
Input envelope + routing for the VPP Judge.

Every predict-row must have:
- inputs_json: stringified JSON with keys {context, generated, ground_truth, compare}
- optional route_hint: "objective" | "subjective" | "both"

This module provides:
- make_envelope(...)  -> convenience helper to build inputs_json
- decide_modes(...)   -> deterministic router
"""

from typing import Optional, Dict, Any
import json


def make_envelope(
    *,
    context: Optional[Dict[str, Any]] = None,
    generated: Optional[Dict[str, str]] = None,       # {"id","text"}
    ground_truth: Optional[Dict[str, str]] = None,    # {"id","text"}
    compare: Optional[Dict[str, Dict[str, str]]] = None,  # {"a":{"id","text"},"b":{"id","text"}}
) -> str:
    """Return a stringified JSON envelope accepted by the judge."""
    payload = {
        "context": context or {},
        "generated": generated or {},
        "ground_truth": ground_truth or {},
        "compare": compare or {},
    }
    return json.dumps(payload, ensure_ascii=False)


def _has_text(d: Optional[Dict[str, Any]], *keys) -> bool:
    cur = d or {}
    for k in keys:
        cur = cur.get(k, {})
    if isinstance(cur, str):
        return bool(cur.strip())
    return False


def decide_modes(route_hint: Optional[str], payload: Dict[str, Any]):
    """
    Decide which judge components to run based on the payload.
    Priority (if no hint):
      - both  : if ground_truth.text and (compare.* OR generated+context) present
      - objective : if ground_truth.text present
      - subjective (pairwise) : if compare.a.text and compare.b.text present
      - subjective_single : if generated.text and context present
    """
    hint = (route_hint or "").strip().lower()
    have_gt = _has_text(payload.get("ground_truth"), "text")
    have_pair = _has_text(payload.get("compare"), "a", "text") and _has_text(payload.get("compare"), "b", "text")
    have_single = _has_text(payload.get("generated"), "text")
    have_ctx = bool(payload.get("context"))

    if hint in {"objective", "subjective", "both"}:
        # Validate mandatory fields for the hinted route
        if hint == "objective" and not have_gt:
            raise ValueError("route_hint=objective requires ground_truth.text")
        if hint == "subjective" and not (have_pair or (have_single and have_ctx)):
            raise ValueError("route_hint=subjective requires compare.* or generated+context")
        if hint == "both" and not (have_gt and (have_pair or (have_single and have_ctx))):
            raise ValueError("route_hint=both requires ground_truth + (compare or generated+context)")
        return ["objective", "subjective"] if hint == "both" else [hint]

    # Auto routing
    modes = []
    if have_gt and (have_pair or (have_single and have_ctx)):
        return ["objective", "subjective"]  # run both; subjective_single handled as 'subjective'
    if have_gt:
        return ["objective"]
    if have_pair:
        return ["subjective"]
    if have_single and have_ctx:
        return ["subjective_single"]
    raise ValueError("No evaluable inputs: provide ground_truth.text OR compare.{a,b}.text OR generated.text + context")
