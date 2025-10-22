# Databricks notebook source
# MAGIC %pip install -U \
# MAGIC   langchain-community \
# MAGIC   databricks-sdk \
# MAGIC   requests \
# MAGIC   tenacity \
# MAGIC   PyPDF2 \
# MAGIC   pdfplumber \
# MAGIC   pymupdf \
# MAGIC   pypdfium2
# MAGIC

# COMMAND ----------

# === ONE-CELL: predict (objective & subjective examples) + optional persist ===
import mlflow, pandas as pd, json, os

# (1) If your subjective path (helpers.call_sonnet) uses OAuth, ensure these are set.
#     If you don't have OAuth creds, skip this block or set via Cluster > Advanced > Env Vars.
# os.environ["DATABRICKS_HOST"] = "https://npm-sandbox.cloud.databricks.com"
# os.environ["DATABRICKS_CLIENT_ID"] = "<client-id>"
# os.environ["DATABRICKS_CLIENT_SECRET"] = "<client-secret>"

# (2) Load the model you just registered (Workspace registry)
MODEL_URI = "models:/vpp_judge/1"
m = mlflow.pyfunc.load_model(MODEL_URI)

# (3) Objective example (candidate vs GT)
payload_obj = {
    "generated":    {"id":"cand1","text":"Brief One-Liner...\nOncologic History..."},
    "ground_truth": {"id":"gt1","text":"Brief One-Liner...\nOncologic History..."}
}
df_obj = pd.DataFrame({
    "inputs_json": [json.dumps(payload_obj)],
    "route_hint":  ["objective"]
})
print("Objective →")
display(m.predict(df_obj))

# (4) Subjective single example (no GT; uses context as original MD note)
payload_subj = {
    "generated": {"id":"candX","text":"Brief One-Liner...\nOncologic History...\n(pretend full note)"},
    "context":   {"textract_text": "Original MD note text here\n(pretend full MD note)"}
}
df_subj = pd.DataFrame({
    "inputs_json": [json.dumps(payload_subj)],
    "route_hint":  ["subjective"]
})
print("Subjective (single) →")
display(m.predict(df_subj))

# (5) OPTIONAL: append objective results to a Delta table (create it once if needed)
# spark.sql("""
# CREATE TABLE IF NOT EXISTS ai_staging.campaign_3.judge_runs (
#   route STRING,
#   obj_closeness DOUBLE,
#   obj_rationale STRING,
#   obj_n_judges INT,
#   obj_details_json STRING,
#   obj_has_brief INT, obj_has_history INT, obj_correct_order INT, obj_has_mmddyyyy INT,
#   subj_preferred STRING, subj_score_a DOUBLE, subj_score_b DOUBLE,
#   subj_vppcomp_a DOUBLE, subj_vppcomp_b DOUBLE, subj_n_judges INT, subj_details_json STRING,
#   subj_relevance STRING, subj_coherence STRING, subj_completeness STRING, subj_correctness STRING,
#   subj_final_relevance STRING, subj_final_completeness STRING, subj_final_correctness STRING,
#   subj_vpp_level STRING, subj_vpp_weighted DOUBLE, subj_passfail STRING, subj_overall_rating STRING,
#   subj_summary_json STRING,
#   elapsed_total_sec DOUBLE,
#   error_code STRING, error_msg STRING,
#   processed_at TIMESTAMP DEFAULT current_timestamp()
# ) USING DELTA
# """)
# spark.createDataFrame(m.predict(df_obj)).write.mode("append").saveAsTable("ai_staging.campaign_3.judge_runs")
# print("✅ wrote objective result to ai_staging.campaign_3.judge_runs")


# COMMAND ----------

dbutils.library.restartPython()

# re-add your src path
SRC_DIR = "/Workspace/Users/karthiksheshadri@npowermedicine.com/vpp_judge/src"
import sys, importlib
if SRC_DIR not in sys.path: sys.path.insert(0, SRC_DIR)
importlib.invalidate_caches()

# sanity
import update_note as UN
print("✅ update_note imported via:", UN.ChatDatabricks.__module__)


# COMMAND ----------

# CRITICAL: Clear service principal env vars before registration
import os
for key in ['DATABRICKS_CLIENT_ID', 'DATABRICKS_CLIENT_SECRET', 'DATABRICKS_HOST']:
    os.environ.pop(key, None)

# Now run registration with YOUR credentials
import mlflow
from mlflow.models.signature import infer_signature

mlflow.set_registry_uri("databricks")

# Create/get experiment
try:
    experiment_id = mlflow.create_experiment("/Shared/vpp_runner_experiments")
    print(f"✅ Created experiment: {experiment_id}")
except:
    experiment = mlflow.get_experiment_by_name("/Shared/vpp_runner_experiments")
    experiment_id = experiment.experiment_id
    print(f"✅ Using existing experiment: {experiment_id}")

mlflow.set_experiment(experiment_id=experiment_id)

runner_reqs = [
    "langchain-community","databricks-sdk",
    "requests","tenacity","PyPDF2","pdfplumber","pymupdf","pypdfium2","pandas",
    "boto3","Pillow","langgraph","databricks-langchain"
]

example_spec = {
    "task":"stylize",
    "dataset":{"source":"uc","table":"ai_staging.campaign_3.vpp_eval_stylize_mm_20250827","limit":2},
    "vary_models":["auto"]
}
input_example = {"spec_json": json.dumps(example_spec)}
sig = infer_signature(
    pd.DataFrame([input_example]),
    pd.DataFrame([{"summary_json":"{}", "report_html_path":"/tmp/report.html"}])
)

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="vpp_runner",
        python_model=VPPRunner(),
        code_paths=[SRC_DIR],
        pip_requirements=runner_reqs,
        registered_model_name="vpp_runner",
        input_example=input_example,
        signature=sig
    )

print("✅ Registered 'vpp_runner' v4!")

# COMMAND ----------

# ===================== REGISTER vpp_runner (COMPLETE WITH MODEL REGISTRY) =====================
import sys, os, json, time, io, base64, importlib, re, boto3
from datetime import datetime
from io import StringIO
from typing import List
from urllib.parse import urlparse
from collections import defaultdict
import pandas as pd
import mlflow, mlflow.pyfunc
from PIL import Image
import pypdfium2 as pdfium

# Make src importable
SRC_DIR = "/Workspace/Users/karthiksheshadri@npowermedicine.com/vpp_judge/src"
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
importlib.invalidate_caches()

# Import modules
import style_transfer as ST
import update_note as UN

from langchain_community.chat_models import ChatDatabricks
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate

# ========== MODEL REGISTRY ==========
MODEL_REGISTRY = [
    {"name":"gpt_oss_120b",      "endpoint":"databricks-gpt-oss-120b",                 "kind":"chat"},
    {"name":"claude_sonnet_3_7", "endpoint":"databricks-claude-3-7-sonnet",            "kind":"chat"},
    {"name":"claude_sonnet_4",   "endpoint":"databricks-claude-sonnet-4",              "kind":"chat"},
    {"name":"claude_sonnet_4_5", "endpoint":"databricks-claude-sonnet-4-5",            "kind":"chat"},
    {"name":"llama4_maverick",   "endpoint":"databricks-llama-4-maverick",             "kind":"chat"},
    {"name":"claude_opus_4",     "endpoint":"databricks-claude-opus-4",                "kind":"chat"},
    {"name":"llama3_3_70b",      "endpoint":"databricks-meta-llama-3-3-70b-instruct",  "kind":"chat"},
]

DEFAULT_MODELS = ["claude_sonnet_4_5", "llama4_maverick", "gpt_oss_120b"]

def get_endpoint(name_or_endpoint: str) -> str:
    """Resolve model name to endpoint."""
    for model in MODEL_REGISTRY:
        if model["name"] == name_or_endpoint:
            return model["endpoint"]
    return name_or_endpoint  # Already an endpoint

# ---- S3 & Textract helpers ----
def _parse_s3(u: str):
    p = urlparse(u) if isinstance(u, str) else None
    return (p.netloc, p.path.lstrip("/")) if p and p.scheme.lower() == "s3" else (None, None)

def _get_s3_bytes(s3_client, s3_uri: str, cap_bytes: int = 15*1024*1024) -> bytes:
    bkt, key = _parse_s3(s3_uri)
    if not bkt: return b""
    obj = s3_client.get_object(Bucket=bkt, Key=key)
    stream = obj["Body"]
    out = io.BytesIO(); total = 0
    for chunk in iter(lambda: stream.read(1024*1024), b""):
        out.write(chunk); total += len(chunk)
        if total >= cap_bytes: break
    return out.getvalue()

def textract_ocr_text(textract_client, s3_uri: str, timeout_s: int = 75) -> str:
    bkt, key = _parse_s3(s3_uri)
    if not bkt: return ""
    try:
        b = _get_s3_bytes(boto3.client("s3"), s3_uri, cap_bytes=10*1024*1024)
        if b:
            resp = textract_client.analyze_document(Document={"Bytes": b}, FeatureTypes=["LAYOUT"])
            lines = [blk["Text"] for blk in resp.get("Blocks", []) if blk.get("BlockType")=="LINE" and "Text" in blk]
            if lines: return "\n".join(lines)
    except Exception:
        pass
    job = textract_client.start_document_analysis(
        DocumentLocation={"S3Object":{"Bucket": bkt, "Name": key}}, FeatureTypes=["LAYOUT"])
    jid = job["JobId"]; lines=[]; t0=time.time()
    while time.time()-t0 < timeout_s:
        st = textract_client.get_document_analysis(JobId=jid)
        if st.get("JobStatus") in ("SUCCEEDED","FAILED","PARTIAL_SUCCESS"):
            blocks = st.get("Blocks", [])
            lines += [blk["Text"] for blk in blocks if blk.get("BlockType")=="LINE" and "Text" in blk]
            nt = st.get("NextToken")
            while nt:
                st = textract_client.get_document_analysis(JobId=jid, NextToken=nt)
                blocks = st.get("Blocks", [])
                lines += [blk["Text"] for blk in blocks if blk.get("BlockType")=="LINE" and "Text" in blk]
                nt = st.get("NextToken")
            break
        time.sleep(5)
    return "\n".join(lines)

# ---- PDF→image rendering ----
def render_pdf_pages_to_urls_from_bytes(b: bytes, max_pages=8, dpi=120, jpeg_quality=65, crop_percent=5) -> List[str]:
    try:
        doc = pdfium.PdfDocument(b)
    except Exception:
        return []
    n = min(len(doc), int(max_pages)); out=[]
    for i in range(n):
        img = doc[i].render(scale=dpi/72.0).to_pil()
        if crop_percent:
            w,h = img.size; dy = int(h*crop_percent/100.0)
            img = img.crop((0, dy, w, h-dy))
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
        out.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8"))
    doc.close()
    return out

def to_image_batches(urls: List[str], bs=3):
    batches=[]
    for i in range(0, len(urls), bs):
        seg = urls[i:i+bs]
        blk = [{"type":"text","text":"Documents Begin..."},
               *({"type":"image_url","image_url":{"url":u}} for u in seg),
               {"type":"text","text":"Documents End."}]
        batches.append(blk)
    return batches

def load_vpp_manual():
    path = os.path.join(SRC_DIR, "vpp_guidelines.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

VPP_MANUAL = load_vpp_manual()

GEN_MAX_TOKENS = 3800
TEMPERATURE = 0.0

IMG_SYS = SystemMessagePromptTemplate.from_template(
    "You are a VPP (Virtual Physician Partner). Convert the clinical images into a VPP note "
    "with STRICT adherence to the VPP guidelines below.\n\n"
    "VPP Guidelines Begin...\n"
    f"{VPP_MANUAL}\n"
    "...Guidelines End.\n\n"
    "Sections: 1) Brief One-Liner 2) Oncologic History. Preserve mm/dd/yyyy; bullets start with **mm/dd/yyyy**.\n"
    "Use ONLY information visible in the images. No commentary."
)
IMG_HUM = HumanMessagePromptTemplate.from_template(
    "Create a VPP note dated {date} from this batch.\nReturn ONLY the VPP note.\n\nMost recent partial (if any):\n{partial}"
)
IMG_PROMPT = ChatPromptTemplate.from_messages([IMG_SYS, ("placeholder","{HIL_pdfs}"), IMG_HUM])

def _chat(endpoint: str): 
    return ChatDatabricks(endpoint=endpoint, temperature=TEMPERATURE, max_tokens=GEN_MAX_TOKENS)

def stylize_from_images_llm(endpoint: str, pdf_bytes: bytes, date_str: str) -> str:
    """IMAGES mode: render PDF pages and use vision LLM"""
    urls = render_pdf_pages_to_urls_from_bytes(pdf_bytes)
    if not urls: return ""
    mdl = _chat(endpoint); note=""
    for blk in to_image_batches(urls):
        out = (IMG_PROMPT | mdl).invoke({"HIL_pdfs":[("human", blk)], "date": date_str, "partial": note or "(none)"})
        note = (out.content or "").strip()
    return note


# ---- RUNNER ----
class VPPRunner(mlflow.pyfunc.PythonModel):
    """Intelligent experiment runner with minimal spec requirements."""

    def load_context(self, context):
        self.judge_uri = os.environ.get("VPP_JUDGE_URI", "models:/vpp_judge/1")
        self.judge = mlflow.pyfunc.load_model(self.judge_uri)

    def _has_ground_truth(self, cases: list) -> bool:
        return any(case.get("gt_text") for case in cases)
    
    def _count_candidates(self, spec: dict) -> int:
        models = self._discover_endpoints(spec)
        modes = 2 if spec.get("vary_input_modes", False) else 1
        return len(models) * modes
    
    def _infer_routes(self, cases: list, num_cands: int) -> set:
        has_gt = self._has_ground_truth(cases)
        routes = set()
        if has_gt:
            routes.add("objective")
        if num_cands >= 2:
            routes.add("subjective")
        if not has_gt:
            routes.add("subjective_single")
        return routes

    def _discover_endpoints(self, spec: dict) -> list:
        """Resolve model names to endpoints."""
        V = spec.get("vary_models", ["auto"])
        if V == ["auto"] or not V:
            V = DEFAULT_MODELS
        return [get_endpoint(m) for m in V]

    def _fetch_cases(self, spec: dict):
        """Fetch cases from UC eval tables or DMS."""
        src = ((spec.get("dataset") or {}).get("source") or "uc").lower()
        
        if src == "dms":
            DMS_TBL = spec["dataset"]["table"]
            mrn = spec["dataset"].get("mrn")
            site = spec["dataset"].get("site")
            limit = int(spec["dataset"].get("limit") or 25)

            from pyspark.sql import functions as F
            j = F.get_json_object
            base = (spark.table(DMS_TBL)
                      .select(
                        F.col("id").alias("doc_id"),
                        F.col("site"),
                        F.col("location"),
                        j(F.col("metadata"), "$.mrn").alias("mrn"),
                        j(F.col("metadata"), "$.document.documentType").alias("doc_type"),
                        j(F.col("metadata"), "$.document.documentDateOrigination").alias("doc_date"))
                      .withColumn("doc_ts", F.to_timestamp("doc_date"))
                      .where(F.col("doc_ts").isNotNull()))
            if mrn: base = base.where(F.col("mrn")==mrn)
            if site: base = base.where(F.upper(F.col("site"))==F.upper(F.lit(site)))
            rows = (base.orderBy(F.col("doc_ts").desc()).limit(limit).collect())
            
            cases = []
            for i, r in enumerate(rows, 1):
                cases.append({
                    "id": f"case_{i}",
                    "s3_uri": r["location"],
                    "gt_text": None,
                    "md_ids": [],
                    "md_text": None,
                    "pdf_path": None
                })
            return cases
        
        # UC eval tables
        ds = spec.get("dataset") or {}
        table = ds.get("table")
        where = ds.get("where")
        limit = int(ds.get("limit") or 50)
        task = (spec.get("task") or "stylize").lower()
        
        TEXT_TABLE = "ai_staging.campaign_3.vpp_all_documents_text"
        
        if not table:
            return []
        
        base = spark.table(table)
        if where:
            base = base.where(where)
        
        if task == "stylize":
            rows = base.select("base_md_id", "gt_vpp_id").limit(limit).collect()
            
            cases = []
            for i, r in enumerate(rows, 1):
                md_text_result = spark.sql(f"SELECT text_content FROM {TEXT_TABLE} WHERE doc_id = '{r['base_md_id']}'").collect()
                gt_text_result = spark.sql(f"SELECT text_content FROM {TEXT_TABLE} WHERE doc_id = '{r['gt_vpp_id']}'").collect()
                
                cases.append({
                    "id": f"case_{i}",
                    "gt_text": gt_text_result[0]["text_content"] if gt_text_result else None,
                    "md_ids": [r["base_md_id"]],
                    "md_text": md_text_result[0]["text_content"] if md_text_result else None,
                    "pdf_path": None,
                    "updates_text": [],
                    "updates_pdf": []
                })
            return cases
        
        elif task == "augment":
            from pyspark.sql import functions as F
            from pyspark.sql.types import ArrayType, StringType
            
            rows = base.select(
                "base_md_id",
                F.from_json("update_ids_json", ArrayType(StringType())).alias("update_ids"),
                "gt_updated_vpp_id"
            ).limit(limit).collect()
            
            cases = []
            for i, r in enumerate(rows, 1):
                md_text_result = spark.sql(f"SELECT text_content FROM {TEXT_TABLE} WHERE doc_id = '{r['base_md_id']}'").collect()
                
                update_ids = r["update_ids"] or []
                updates_text = []
                for uid in update_ids:
                    u_text = spark.sql(f"SELECT text_content FROM {TEXT_TABLE} WHERE doc_id = '{uid}'").collect()
                    if u_text:
                        updates_text.append(u_text[0]["text_content"])
                
                gt_text_result = spark.sql(f"SELECT text_content FROM {TEXT_TABLE} WHERE doc_id = '{r['gt_updated_vpp_id']}'").collect()
                
                cases.append({
                    "id": f"case_{i}",
                    "gt_text": gt_text_result[0]["text_content"] if gt_text_result else None,
                    "md_ids": [r["base_md_id"]] + update_ids,
                    "md_text": md_text_result[0]["text_content"] if md_text_result else None,
                    "pdf_path": None,
                    "updates_text": updates_text,
                    "updates_pdf": []
                })
            return cases
        
        return []

    def _generate_candidates(self, spec: dict, cases: list, endpoints: list):
        """Generate candidates with configurable parameters."""
        task = (spec.get("task") or "stylize").lower()
        vary_modes = bool(spec.get("vary_input_modes", False))
        today = datetime.now().strftime("%m/%d/%Y")
        src = ((spec.get("dataset") or {}).get("source") or "uc").lower()
        
        # Get generation parameters
        gen = spec.get("generation", {})
        temperature = gen.get("temperature", 0.0)
        max_tokens = gen.get("max_tokens", 5000)

        out = []
        
        # STYLIZE from DMS
        if task == "stylize" and src == "dms":
            chat_ep = endpoints[0] if endpoints else "databricks-claude-sonnet-4-5"
            
            TEXTRACT_REGION = spec.get("aws",{}).get("region","us-west-2")
            textract_client = boto3.client("textract", region_name=TEXTRACT_REGION)
            s3_client = boto3.client("s3", region_name=TEXTRACT_REGION)

            for case in cases:
                # TEXT mode
                try:
                    ocr = textract_ocr_text(textract_client, case["s3_uri"], timeout_s=75)
                    case["md_text"] = ocr
                    
                    if ocr:
                        cand_text = ST.execute_style_transfer_text(
                            ocr, today, 
                            model_endpoint=chat_ep,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    else:
                        cand_text = "(gen_error) no OCR text extracted"
                except Exception as e:
                    cand_text = f"(gen_error) {str(e)[:240]}"
                
                out.append({
                    "case_id": case["id"],
                    "candidate_id": f"{chat_ep}:text",
                    "endpoint": chat_ep,
                    "mode": "text",
                    "text": cand_text
                })

                # IMAGES mode
                if vary_modes:
                    try:
                        pdf_bytes = _get_s3_bytes(s3_client, case["s3_uri"], cap_bytes=12*1024*1024)
                        if pdf_bytes and pdf_bytes[:4]==b"%PDF":
                            cand_img = stylize_from_images_llm(chat_ep, pdf_bytes, today)
                        else:
                            cand_img = "(gen_error) invalid PDF bytes"
                    except Exception as e:
                        cand_img = f"(gen_error) {str(e)[:240]}"
                    
                    out.append({
                        "case_id": case["id"],
                        "candidate_id": f"{chat_ep}:images",
                        "endpoint": chat_ep,
                        "mode": "images",
                        "text": cand_img
                    })
            return out

        # STYLIZE from UC
        if task == "stylize" and src == "uc":
            for case in cases:
                base_text = case.get("md_text") or ""
                for ep in endpoints:
                    try:
                        vpp = ST.execute_style_transfer_text(
                            base_text, today,
                            model_endpoint=ep,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        out.append({
                            "case_id": case["id"],
                            "candidate_id": f"{ep}:text",
                            "endpoint": ep,
                            "mode": "text",
                            "text": vpp
                        })
                    except Exception as e:
                        out.append({
                            "case_id": case["id"],
                            "candidate_id": f"{ep}:text",
                            "endpoint": ep,
                            "mode": "text",
                            "text": f"(gen_error) {str(e)[:240]}"
                        })
            return out

        # AUGMENT
        if task == "augment":
            for case in cases:
                base_text = case.get("md_text") or ""
                try:
                    seed = ST.execute_style_transfer_text(
                        base_text, today,
                        model_endpoint=endpoints[0],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                except Exception as e:
                    seed = f"(seed_error) {str(e)[:240]}"
                
                for ep in endpoints:
                    try:
                        note = seed
                        for pdf_path in (case.get("updates_pdf") or []):
                            if pdf_path:
                                imgs = UN.pdf_pages_b64(pdf_path, pages=3, dpi=300)
                                content, meta = UN.append_to_vpp_note(
                                    most_recent_note=note,
                                    most_recent_note_date=today,
                                    current_day=today,
                                    page_images=imgs,
                                    model_endpoint=ep,
                                    temperature=temperature,
                                    max_tokens=max_tokens
                                )
                                note = content
                        out.append({
                            "case_id": case["id"],
                            "candidate_id": f"{ep}:images",
                            "endpoint": ep,
                            "mode": "images",
                            "text": note
                        })
                    except Exception as e:
                        out.append({
                            "case_id": case["id"],
                            "candidate_id": f"{ep}:images",
                            "endpoint": ep,
                            "mode": "images",
                            "text": f"(augment_error) {str(e)[:240]}"
                        })
            return out

        return out

    def _build_envelopes(self, cases: list, candidates: list):
        """Build judge payloads."""
        by_case = defaultdict(list)
        for c in candidates:
            by_case[c["case_id"]].append(c)

        rows = []
        for case in cases:
            cands = by_case.get(case["id"], [])
            cands.sort(key=lambda x: (x["endpoint"], x["mode"]))
            
            routes = self._infer_routes([case], len(cands))

            # OBJECTIVE
            if "objective" in routes and case.get("gt_text"):
                for c in cands:
                    if c["text"].startswith("(") or c["text"].startswith("Error:"):
                        continue
                    payload = {
                        "generated": {"id": c["candidate_id"], "text": c["text"]},
                        "ground_truth": {"id": f"{case['id']}_gt", "text": case["gt_text"]}
                    }
                    rows.append({"inputs_json": json.dumps(payload), "route_hint": "objective"})

            # SUBJECTIVE PAIRWISE
            if "subjective" in routes and len(cands) >= 2:
                for i in range(len(cands)-1):
                    a, b = cands[i], cands[i+1]
                    if a["text"].startswith("(") or a["text"].startswith("Error:") or \
                       b["text"].startswith("(") or b["text"].startswith("Error:"):
                        continue
                    payload = {
                        "compare": {
                            "a": {"id": a["candidate_id"], "text": a["text"]},
                            "b": {"id": b["candidate_id"], "text": b["text"]}
                        }
                    }
                    if case.get("gt_text"):
                        payload["ground_truth"] = {"id": f"{case['id']}_gt", "text": case["gt_text"]}
                    rows.append({"inputs_json": json.dumps(payload), "route_hint": "subjective"})

            # SUBJECTIVE SINGLE
            if "subjective_single" in routes and case.get("md_text"):
                for c in cands:
                    if c["text"].startswith("(") or c["text"].startswith("Error:"):
                        continue
                    payload = {
                        "generated": {"id": c["candidate_id"], "text": c["text"]},
                        "context": {"textract_text": case["md_text"]}
                    }
                    rows.append({"inputs_json": json.dumps(payload), "route_hint": "subjective"})
        
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["inputs_json","route_hint"])

    def _judge(self, df_rows: pd.DataFrame):
        if len(df_rows)==0: return pd.DataFrame()
        return self.judge.predict(df_rows)

    def _write_report(self, spec: dict, judged: pd.DataFrame):
        base = ((spec.get("report") or {}).get("base_path") or "/tmp/judge/reports").rstrip("/")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = f"{base}/{spec.get('name','exp')}_{ts}.html"
        html = StringIO()
        html.write("<html><body>")
        html.write(f"<h2>VPP Experiment: {spec.get('name')}</h2>")
        html.write(f"<p>Task: {spec.get('task')} | Judge: {self.judge_uri}</p>")
        html.write(f"<p>Judged: {len(judged)} rows</p>")
        if "obj_closeness" in judged.columns:
            html.write("<h3>Objective (mean closeness)</h3>")
            try:
                mc = float(judged["obj_closeness"].dropna().mean())
                html.write(f"<p>{mc:.3f}</p>")
            except Exception:
                html.write("<p>N/A</p>")
        if "subj_preferred" in judged.columns:
            html.write("<h3>Pairwise preferred</h3>")
            html.write(judged["subj_preferred"].fillna("tie").value_counts().to_frame("count").to_html())
        html.write("<h3>Sample rows</h3>")
        html.write(judged.head(30).to_html(index=False, escape=False))
        html.write("</body></html>")
        
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html.getvalue())
        return html_path

    def predict(self, context, df: pd.DataFrame) -> pd.DataFrame:
        if "spec_json" not in df.columns:
            raise ValueError("vpp_runner expects a DataFrame with a 'spec_json' string column")
        spec = json.loads(df.iloc[0]["spec_json"])

        endpoints = self._discover_endpoints(spec)
        cases = self._fetch_cases(spec)
        cands = self._generate_candidates(spec, cases, endpoints)
        rows_df = self._build_envelopes(cases, cands)
        judged = self._judge(rows_df)

        persist = (spec.get("persist") or {})
        if persist.get("save_to_delta") and len(judged):
            spark.createDataFrame(judged).write.mode("append").saveAsTable(
                persist.get("table","ai_staging.campaign_3.judge_runs"))

        report_html = self._write_report(spec, judged)
        
        summary = {
            "spec": spec,
            "judge_uri": self.judge_uri,
            "n_cases": len(cases),
            "n_candidates": len(cands),
            "n_envelopes": int(len(rows_df)),
            "n_judged": int(len(judged)),
            "report_html_path": report_html
        }
        return pd.DataFrame([{
            "summary_json": json.dumps(summary),
            "report_html_path": report_html
        }])


# ========== REGISTER ==========
from mlflow.models.signature import infer_signature

mlflow.set_registry_uri("databricks")

runner_reqs = [
    "langchain-community","databricks-sdk",
    "requests","tenacity","PyPDF2","pdfplumber","pymupdf","pypdfium2","pandas",
    "boto3","Pillow","langgraph","databricks-langchain"
]

example_spec = {
    "task":"stylize",
    "dataset":{"source":"uc","table":"ai_staging.campaign_3.vpp_eval_stylize_mm_20250827","limit":2},
    "vary_models":["auto"]
}
input_example = {"spec_json": json.dumps(example_spec)}
sig = infer_signature(
    pd.DataFrame([input_example]),
    pd.DataFrame([{"summary_json":"{}", "report_html_path":"/tmp/report.html"}])
)

# ========== REGISTER (CREATE EXPERIMENT FIRST) ==========
from mlflow.models.signature import infer_signature

mlflow.set_registry_uri("databricks")

# Create/get experiment explicitly
try:
    experiment_id = mlflow.create_experiment("/Shared/vpp_runner_experiments")
    print(f"✅ Created experiment: {experiment_id}")
except Exception as e:
    # Experiment already exists, get it
    experiment = mlflow.get_experiment_by_name("/Shared/vpp_runner_experiments")
    experiment_id = experiment.experiment_id
    print(f"✅ Using existing experiment: {experiment_id}")

mlflow.set_experiment(experiment_id=experiment_id)

runner_reqs = [
    "langchain-community","databricks-sdk",
    "requests","tenacity","PyPDF2","pdfplumber","pymupdf","pypdfium2","pandas",
    "boto3","Pillow","langgraph","databricks-langchain"
]

example_spec = {
    "task":"stylize",
    "dataset":{"source":"uc","table":"ai_staging.campaign_3.vpp_eval_stylize_mm_20250827","limit":2},
    "vary_models":["auto"]
}
input_example = {"spec_json": json.dumps(example_spec)}
sig = infer_signature(
    pd.DataFrame([input_example]),
    pd.DataFrame([{"summary_json":"{}", "report_html_path":"/tmp/report.html"}])
)

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="vpp_runner",
        python_model=VPPRunner(),
        code_paths=[SRC_DIR],
        pip_requirements=runner_reqs,
        registered_model_name="vpp_runner",
        input_example=input_example,
        signature=sig
    )

print("✅ Registered 'vpp_runner' v4 - Complete!")

# COMMAND ----------

# Install missing dependencies
%pip install langgraph databricks-langchain --quiet
dbutils.library.restartPython()

import os, sys, mlflow, pandas as pd, json

# Add src to path FIRST
SRC_DIR = "/Workspace/Users/karthiksheshadri@npowermedicine.com/vpp_judge/src"
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Set registry URI
mlflow.set_registry_uri("databricks")

# Clear env vars
for key in ['DATABRICKS_CLIENT_ID', 'DATABRICKS_CLIENT_SECRET', 'DATABRICKS_HOST']:
    os.environ.pop(key, None)

os.environ["TMPDIR"] = "/tmp"

# Now load model
runner = mlflow.pyfunc.load_model("models:/vpp_runner/6")

# Set credentials
client_id = dbutils.secrets.get("service-principals", "vpp-app-client-id")
client_secret = dbutils.secrets.get("service-principals", "vpp-app-client-secret")
os.environ["DATABRICKS_HOST"] = "https://npm-sandbox.cloud.databricks.com"
os.environ["DATABRICKS_CLIENT_ID"] = client_id
os.environ["DATABRICKS_CLIENT_SECRET"] = client_secret

print("🧪 TESTING VPP_RUNNER V6")

spec = {
    "name": "test_run_v6",
    "task": "stylize",
    "dataset": {
        "source": "uc",
        "table": "ai_staging.campaign_3.vpp_eval_stylize_mm_20250827",
        "limit": 2
    }
}

df = pd.DataFrame({"spec_json": [json.dumps(spec)]})
result = runner.predict(df)
summary = json.loads(result.iloc[0]["summary_json"])

print(json.dumps(summary, indent=2))

if summary['n_judged'] > 0:
    print(f"\n✅ SUCCESS! Judged {summary['n_judged']} rows")
    with open(summary['report_html_path'], 'r') as f:
        displayHTML(f.read())
else:
    print(f"\n❌ Failed: n_envelopes={summary['n_envelopes']}, n_candidates={summary['n_candidates']}")

import os, mlflow, pandas as pd, json

# Set registry URI FIRST
mlflow.set_registry_uri("databricks")

# Clear env vars
for key in ['DATABRICKS_CLIENT_ID', 'DATABRICKS_CLIENT_SECRET', 'DATABRICKS_HOST']:
    os.environ.pop(key, None)

os.environ["TMPDIR"] = "/tmp"

# Now load model
runner = mlflow.pyfunc.load_model("models:/vpp_runner/6")

# Set credentials
client_id = dbutils.secrets.get("service-principals", "vpp-app-client-id")
client_secret = dbutils.secrets.get("service-principals", "vpp-app-client-secret")
os.environ["DATABRICKS_HOST"] = "https://npm-sandbox.cloud.databricks.com"
os.environ["DATABRICKS_CLIENT_ID"] = client_id
os.environ["DATABRICKS_CLIENT_SECRET"] = client_secret

print("🧪 TESTING VPP_RUNNER V6")

spec = {
    "name": "test_run_v6",
    "task": "stylize",
    "dataset": {
        "source": "uc",
        "table": "ai_staging.campaign_3.vpp_eval_stylize_mm_20250827",
        "limit": 2
    }
}

df = pd.DataFrame({"spec_json": [json.dumps(spec)]})
result = runner.predict(df)
summary = json.loads(result.iloc[0]["summary_json"])

print(json.dumps(summary, indent=2))

if summary['n_judged'] > 0:
    print(f"\n✅ SUCCESS! Judged {summary['n_judged']} rows")
    with open(summary['report_html_path'], 'r') as f:
        displayHTML(f.read())
else:
    print(f"\n❌ n_envelopes: {summary['n_envelopes']}")

# COMMAND ----------

import os, sys, mlflow, pandas as pd, json

SRC_DIR = "/Workspace/Users/karthiksheshadri@npowermedicine.com/vpp_judge/src"
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

mlflow.set_registry_uri("databricks")

for key in ['DATABRICKS_CLIENT_ID', 'DATABRICKS_CLIENT_SECRET', 'DATABRICKS_HOST']:
    os.environ.pop(key, None)

os.environ["TMPDIR"] = "/tmp"

runner = mlflow.pyfunc.load_model("models:/vpp_runner/6")

client_id = dbutils.secrets.get("service-principals", "vpp-app-client-id")
client_secret = dbutils.secrets.get("service-principals", "vpp-app-client-secret")
os.environ["DATABRICKS_HOST"] = "https://npm-sandbox.cloud.databricks.com"
os.environ["DATABRICKS_CLIENT_ID"] = client_id
os.environ["DATABRICKS_CLIENT_SECRET"] = client_secret

# Get the runner instance to debug
runner_model = runner._model_impl.python_model

spec = {
    "name": "test_debug",
    "task": "stylize",
    "dataset": {"source": "uc", "table": "ai_staging.campaign_3.vpp_eval_stylize_mm_20250827", "limit": 1}
}

# Debug step by step
endpoints = runner_model._discover_endpoints(spec)
print(f"Endpoints: {endpoints}")

cases = runner_model._fetch_cases(spec)
print(f"Cases: {len(cases)}")
print(f"Case 0 has md_text: {len(cases[0].get('md_text', '')) if cases else 0} chars")

cands = runner_model._generate_candidates(spec, cases, endpoints)
print(f"\nCandidates: {len(cands)}")

for i, c in enumerate(cands):
    print(f"\n{i+1}. {c['candidate_id']}")
    print(f"   Text preview: {c['text'][:200]}")
    print(f"   Starts with error? {c['text'].startswith('(') or c['text'].startswith('Error:')}")

# COMMAND ----------

# Check envelope creation
rows_df = runner_model._build_envelopes(cases, cands)
print(f"Envelopes created: {len(rows_df)}")

if len(rows_df) > 0:
    print("\nEnvelope routes:")
    print(rows_df["route_hint"].value_counts())
    print("\nFirst envelope payload:")
    print(json.loads(rows_df.iloc[0]["inputs_json"])["generated"]["id"])
else:
    print("\n❌ NO ENVELOPES - Debugging...")
    print(f"  GT exists: {bool(cases[0].get('gt_text'))}")
    print(f"  GT length: {len(cases[0].get('gt_text', ''))}")
    print(f"  Num candidates: {len(cands)}")
    
    # Check filtering
    print("\n  Candidate filtering:")
    for c in cands:
        starts_paren = c["text"].startswith("(")
        starts_error = c["text"].startswith("Error:")
        filtered = starts_paren or starts_error
        print(f"    {c['candidate_id']}: filtered={filtered} (paren={starts_paren}, error={starts_error})")
    
    # Check what routes would be inferred
    routes = runner_model._infer_routes(cases, len(cands))
    print(f"\n  Routes inferred: {routes}")

# Run the judge!
print("Running judge on 2 envelopes...")
judged = runner_model._judge(rows_df)

print(f"\nJudged: {len(judged)} rows")
print("\nColumns:", judged.columns.tolist())

if len(judged) > 0:
    print("\n✅ JUDGE WORKS!")
    print("\nObjective closeness scores:")
    print(judged[["obj_closeness"]].describe())
    
    print("\nFull results:")
    display(judged)
    
    # Write report
    report_path = runner_model._write_report(spec, judged)
    print(f"\n📊 Report: {report_path}")
    
    with open(report_path, 'r') as f:
        displayHTML(f.read())
else:
    print("❌ Judge returned empty")

# COMMAND ----------

# ========== QUICK MULTI-SPEC TEST (2 cases each) ==========
import os, sys, mlflow, pandas as pd, json
from datetime import datetime

# Setup
SRC_DIR = "/Workspace/Users/karthiksheshadri@npowermedicine.com/vpp_judge/src"
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

mlflow.set_registry_uri("databricks")
for key in ['DATABRICKS_CLIENT_ID', 'DATABRICKS_CLIENT_SECRET', 'DATABRICKS_HOST']:
    os.environ.pop(key, None)
os.environ["TMPDIR"] = "/tmp"

runner = mlflow.pyfunc.load_model("models:/vpp_runner/6")

client_id = dbutils.secrets.get("service-principals", "vpp-app-client-id")
client_secret = dbutils.secrets.get("service-principals", "vpp-app-client-secret")
os.environ["DATABRICKS_HOST"] = "https://npm-sandbox.cloud.databricks.com"
os.environ["DATABRICKS_CLIENT_ID"] = client_id
os.environ["DATABRICKS_CLIENT_SECRET"] = client_secret

# Define quick specs (only working models, 2 cases each)
specs = [
    {
        "name": "baseline_2models",
        "task": "stylize",
        "dataset": {"source": "uc", "table": "ai_staging.campaign_3.vpp_eval_stylize_mm_20250827", "limit": 2},
        "vary_models": ["claude_sonnet_4_5", "llama4_maverick"]
    },
    {
        "name": "sonnet_temp_0",
        "task": "stylize",
        "dataset": {"source": "uc", "table": "ai_staging.campaign_3.vpp_eval_stylize_mm_20250827", "limit": 2},
        "vary_models": ["claude_sonnet_4_5"],
        "generation": {"temperature": 0.0}
    },
    {
        "name": "sonnet_temp_0.3",
        "task": "stylize",
        "dataset": {"source": "uc", "table": "ai_staging.campaign_3.vpp_eval_stylize_mm_20250827", "limit": 2},
        "vary_models": ["claude_sonnet_4_5"],
        "generation": {"temperature": 0.3}
    }
]

# Run all specs and collect results
results = []
for spec in specs:
    print(f"\n{'='*60}")
    print(f"🚀 Running: {spec['name']}")
    start = datetime.now()
    
    df = pd.DataFrame({"spec_json": [json.dumps(spec)]})
    result = runner.predict(df)
    summary = json.loads(result.iloc[0]["summary_json"])
    
    elapsed = (datetime.now() - start).total_seconds()
    print(f"✅ Done in {elapsed:.0f}s - Judged: {summary['n_judged']} rows")
    
    results.append({
        "name": spec["name"],
        "n_candidates": summary["n_candidates"],
        "n_judged": summary["n_judged"],
        "elapsed_sec": elapsed,
        "report": summary["report_html_path"]
    })

# Summary
print(f"\n{'='*60}")
print("📊 FINAL SUMMARY")
print(f"{'='*60}")
summary_df = pd.DataFrame(results)
display(summary_df)

print("\n📄 Reports generated:")
for r in results:
    print(f"  - {r['name']}: {r['report']}")

# COMMAND ----------

# ========== VIEW RESULTS ==========
import pandas as pd

# Show summary table
print("="*60)
print("EXPERIMENT RESULTS")
print("="*60)
display(summary_df)

# Read and display each report
for r in results:
    print(f"\n{'='*60}")
    print(f"📊 {r['name']}")
    print(f"{'='*60}")
    
    try:
        with open(r['report'], 'r') as f:
            displayHTML(f.read())
    except Exception as e:
        print(f"❌ Could not read report: {e}")

# Or check if reports have actual content
print(f"\n{'='*60}")
print("REPORT FILE SIZES")
print(f"{'='*60}")

import os
for r in results:
    if os.path.exists(r['report']):
        size = os.path.getsize(r['report'])
        print(f"{r['name']}: {size:,} bytes")
        
        # Quick peek at content
        with open(r['report'], 'r') as f:
            content = f.read()
            has_closeness = 'obj_closeness' in content
            has_preferred = 'subj_preferred' in content
            print(f"  - Has closeness scores: {has_closeness}")
            print(f"  - Has pairwise comparisons: {has_preferred}")
    else:
        print(f"{r['name']}: FILE NOT FOUND")