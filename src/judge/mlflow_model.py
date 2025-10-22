# src/judge/mlflow_model.py
"""
MLflow pyfunc wrapper for the VPP Judge.

- Single entrypoint: predict(df) where df has columns:
    - inputs_json : stringified envelope (see io_schema.make_envelope)
    - route_hint  : optional ("objective" | "subjective" | "both")
    - config_yaml : optional (present but unused in this minimal v1)

- Self-routing via io_schema.decide_modes
- Defensive per-row error capture so one bad row doesn't fail the batch
"""

from typing import List, Dict, Any
import mlflow
import mlflow.pyfunc
import pandas as pd
import json
import time

from judge.io_schema import decide_modes
from judge.backends import run_objective, run_subjective_pairwise, run_subjective_single


class VPPJudge(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        """
        If you want to load calibration pickles, prompt files, or external config,
        do it here and stash in self. Keep minimal for v1.
        """
        self.loaded = True

    def _predict_row(self, inputs_json: str, route_hint: str | None) -> Dict[str, Any]:
        t0 = time.time()
        payload = json.loads(inputs_json)
        modes = decide_modes(route_hint, payload)

        out: Dict[str, Any] = {"route": ",".join(modes)}
        # Objective judge
        if "objective" in modes:
            out.update(run_objective(payload))
        # Subjective pairwise judge
        if "subjective" in modes:
            out.update(run_subjective_pairwise(payload))
        # Subjective single-note judge
        if "subjective_single" in modes:
            out.update(run_subjective_single(payload))

        out["elapsed_total_sec"] = float(time.time() - t0)
        out["error_code"] = None
        out["error_msg"] = None
        return out

    def predict(self, context, df: pd.DataFrame) -> pd.DataFrame:
        results: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                inputs_json = row.get("inputs_json")
                if not isinstance(inputs_json, str) or not inputs_json.strip():
                    raise ValueError("inputs_json must be a non-empty JSON string")
                route_hint = row.get("route_hint")
                results.append(self._predict_row(inputs_json, route_hint))
            except Exception as e:
                results.append({
                    "route": None,
                    "elapsed_total_sec": 0.0,
                    "error_code": "ROW_FAILED",
                    "error_msg": str(e)[:1000],
                })
        return pd.DataFrame(results)
