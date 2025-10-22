# src/vpp_evaluation.py
"""
VPP Evaluation System Module
Provides functions to evaluate VPP note compliance and quality
"""


VPP_RULES = [
  {"id":"R001","category":"Structure","rule":"Every VPP note starts with a Brief One‑Liner, followed by the Oncological History.","page":10,"weight":5},
  {"id":"R002","category":"Structure","rule":"If a Detailed One‑Liner is used, place it in the Assessment & Plan section, not above the History.","page":14,"weight":5},
  {"id":"R003","category":"Structure","rule":"Insert a Disease Header before each Oncological History block.","page":17,"weight":5},
  {"id":"R004","category":"Structure","rule":"Disease Headers must precede each primary cancer timeline when multiple primaries exist.","page":17,"weight":5},
  {"id":"R005","category":"Structure","rule":"Bulleted History entries are ordered strictly earliest → latest.","page":18,"weight":4},
  {"id":"R006","category":"Structure","rule":"Create a distinct paragraph for each primary diagnosis in reverse‑chronological DOD order.","page":16,"weight":5},
  {"id":"R007","category":"Structure","rule":"Sub‑bullets are used only for nested events tied to the parent date (e.g., drug holds).","page":22,"weight":3},
  {"id":"R008","category":"Structure","rule":"Never merge two distinct clinical events into one bullet; duplicate the date line instead.","page":12,"weight":4},
  {"id":"R009","category":"Structure","rule":"Hospitalisations are documented as a separate bullet spanning the admission date range.","page":24,"weight":3},
  {"id":"R010","category":"Structure","rule":"Long histories (>5 yrs) may be summarised in one bullet except DOD, treatment, and recurrence bullets which stay explicit.","page":25,"weight":3},

  {"id":"R011","category":"Formatting","rule":"Disease Headers are **bold + underlined**.","page":11,"weight":1},
  {"id":"R012","category":"Formatting","rule":"All dates in top‑level bullets are **bold**; dates inside a sub‑bullet are not.","page":12,"weight":1},
  {"id":"R013","category":"Formatting","rule":"Dates use the format MM/DD/YYYY (leading zeros required).","page":12,"weight":2},
  {"id":"R014","category":"Formatting","rule":"Partial dates retain bolding but omit unknown pieces (e.g., 04/2023 or 2023).","page":12,"weight":2},
  {"id":"R015","category":"Formatting","rule":"Approximate seasons map to Jan / Apr / Jul / Oct for Winter / Spring / Summer / Fall.","page":13,"weight":1},
  {"id":"R016","category":"Formatting","rule":"The phrases \"Date of Diagnosis\", histopathology names, Stage/TNM, treatment names, and the words Recurrence / Progression / Metastasis are **bold**.","page":11,"weight":2},
  {"id":"R017","category":"Formatting","rule":"Do **not** use symbols such as + or & between drugs—spell out \"and\".","page":13,"weight":1},
  {"id":"R018","category":"Formatting","rule":"Use the phrase \"consistent with\" when recording pathology findings.","page":20,"weight":1},
  {"id":"R019","category":"Formatting","rule":"Indent second‑level bullets by exactly one tab stop or two spaces.","page":18,"weight":1},
  {"id":"R020","category":"Formatting","rule":"No blank lines between consecutive bullets within the same diagnosis block.","page":18,"weight":1},

  {"id":"R021","category":"Dates","rule":"When multiple source docs share the same date, create separate bullets for each document.","page":12,"weight":3},
  {"id":"R022","category":"Dates","rule":"For biomarker results on archival tissue, use the tissue‑collection date, not the report date.","page":19,"weight":4},
  {"id":"R023","category":"Dates","rule":"Escalate missing dates via the 'missing‑information' process; do not invent dates.","page":13,"weight":4},
  {"id":"R024","category":"Dates","rule":"Date ranges for completed treatments appear as MM/DD/YYYY‑MM/DD/YYYY and are bold.","page":21,"weight":3},
  {"id":"R025","category":"Dates","rule":"Holds or dose reductions appear as sub‑bullets with their own date range.","page":22,"weight":3},
  {"id":"R026","category":"Dates","rule":"For oral SACT with unknown stop date, record only the start date.","page":30,"weight":3},
  {"id":"R027","category":"Dates","rule":"Use collection date ('Collected') from pathology, never the report sign‑out date.","page":25,"weight":4},
  {"id":"R028","category":"Dates","rule":"If MD notes specify \"started X days ago\", back‑calculate actual start date.","page":30,"weight":4},
  {"id":"R029","category":"Dates","rule":"Do not bold dates inside parentheses or within narrative prose.","page":11,"weight":2},
  {"id":"R030","category":"Dates","rule":"Imaging follow‑up lists only the three most‑recent study dates unless abnormal.","page":23,"weight":2},

  {"id":"R031","category":"One‑Liner (Brief)","rule":"Brief One‑Liner always includes Age, Gender, Histopathology, Site/Laterality, and current management.","page":13,"weight":4},
  {"id":"R032","category":"One‑Liner (Brief)","rule":"If Stage IV, prepend the word \"Metastatic\" before histopathology.","page":13,"weight":4},
  {"id":"R033","category":"One‑Liner (Brief)","rule":"If metastasis occurred later, append \"now with metastasis\" after Site/Laterality.","page":13,"weight":3},
  {"id":"R034","category":"One‑Liner (Brief)","rule":"Exclude any mention of \"non‑metastatic\" status.","page":15,"weight":2},
  {"id":"R035","category":"One‑Liner (Brief)","rule":"Current treatment text begins with \"Currently on …\" and lists active systemic or RT modality.","page":14,"weight":3},
  {"id":"R036","category":"One‑Liner (Brief)","rule":"Use full generic or trade names for active drugs—no abbreviations.","page":14,"weight":2},
  {"id":"R037","category":"One‑Liner (Brief)","rule":"Laterality is stated only for paired organs.","page":13,"weight":2},
  {"id":"R038","category":"One‑Liner (Brief)","rule":"Remove trailing periods inside drug lists except the sentence‑final period.","page":13,"weight":1},
  {"id":"R039","category":"One‑Liner (Brief)","rule":"When no active treatment, replace with \"on follow‑up\" or \"on surveillance\".","page":15,"weight":3},
  {"id":"R040","category":"One‑Liner (Brief)","rule":"Do not include biomarker info in the Brief One‑Liner.","page":13,"weight":2},

  {"id":"R041","category":"One‑Liner (Detailed)","rule":"Detailed One‑Liner begins with Age and Gender, then lists biomarkers, Stage/TNM, Grade, Histopathology.","page":14,"weight":3},
  {"id":"R042","category":"One‑Liner (Detailed)","rule":"Include 's/p' phrase summarising key past cancer‑directed therapies.","page":14,"weight":3},
  {"id":"R043","category":"One‑Liner (Detailed)","rule":"If metastatic, include term before biomarkers (e.g., \"Metastatic EGFR‑mutated …\").","page":14,"weight":3},
  {"id":"R044","category":"One‑Liner (Detailed)","rule":"For progression‑related metastasis, insert clause \"now with metastasis\" after the therapy summary.","page":14,"weight":3},
  {"id":"R045","category":"One‑Liner (Detailed)","rule":"Use comma‑separated list for biomarkers in canonical order (e.g., ER, PR, HER2).","page":15,"weight":2},
  {"id":"R046","category":"One‑Liner (Detailed)","rule":"Do not state drug cycles or doses in the One‑Liner.","page":14,"weight":2},
  {"id":"R047","category":"One‑Liner (Detailed)","rule":"Spell out staging as \"Stage IIIA (T2N2M0)\" when TNM known; omit TNM if unknown.","page":14,"weight":3},
  {"id":"R048","category":"One‑Liner (Detailed)","rule":"Use \"Grade #\" (arabic numeral) for histologic grade.","page":14,"weight":2},
  {"id":"R049","category":"One‑Liner (Detailed)","rule":"Never split a Detailed One‑Liner across lines—keep as one paragraph.","page":14,"weight":2},
  {"id":"R050","category":"One‑Liner (Detailed)","rule":"When both one‑liners are present, the Brief precedes the Detailed.","page":14,"weight":3},

  {"id":"R051","category":"History","rule":"Presenting Symptom bullet contains symptom description or incidental finding and its date.","page":18,"weight":3},
  {"id":"R052","category":"History","rule":"Diagnostic/Staging Work‑up bullets list date, test name, and concise impression only.","page":18,"weight":3},
  {"id":"R053","category":"History","rule":"Imaging bullets include measurement details only if clinically relevant.","page":18,"weight":2},
  {"id":"R054","category":"History","rule":"Biopsy bullets list specimen source and major biomarkers in one sentence.","page":19,"weight":3},
  {"id":"R055","category":"History","rule":"All positive and key negative biomarkers must be captured when reported.","page":19,"weight":3},
  {"id":"R056","category":"History","rule":"Use a sub‑bullet under the tissue‑collection date for later genomic testing on that specimen.","page":19,"weight":3},
  {"id":"R057","category":"History","rule":"Mark the first malignant pathology bullet with the phrase \"Date of Diagnosis\".","page":20,"weight":5},
  {"id":"R058","category":"History","rule":"Surgical pathology bullets enumerate margins and nodal status if reported.","page":20,"weight":3},
  {"id":"R059","category":"History","rule":"Radiation therapy bullets show modality, site, total Gy, and total fractions.","page":21,"weight":3},
  {"id":"R060","category":"History","rule":"Systemic therapy bullets list start date and drugs; if cycles known, add \"x N cycles\".","page":21,"weight":3},
  {"id":"R061","category":"History","rule":"Systemic therapy holds or doses reductions appear as sub‑bullets with reason.","page":22,"weight":3},
  {"id":"R062","category":"History","rule":"When a drug is stopped, include discontinue reason in same line.","page":22,"weight":3},
  {"id":"R063","category":"History","rule":"Clinical‑trial bullets begin with protocol/study name before listing drugs.","page":22,"weight":3},
  {"id":"R064","category":"History","rule":"Concurrent chemo‑radiation is recorded as separate bullets, ordered by start date.","page":22,"weight":3},
  {"id":"R065","category":"History","rule":"Follow‑up/Surveillance section lists only imaging or labs used to monitor for recurrence.","page":23,"weight":2},
  {"id":"R066","category":"History","rule":"If on follow‑up < 1 yr, list every imaging study; if > 1 yr, summarise with date range.","page":23,"weight":2},
  {"id":"R067","category":"History","rule":"Recurrence/Progression/Metastasis terms are bolded only when confirmed by physician.","page":24,"weight":3},
  {"id":"R068","category":"History","rule":"If radiologist report and MD disagree, follow MD assessment for bolding.","page":24,"weight":3},
  {"id":"R069","category":"History","rule":"Hospitalization bullets include admission date range, reason, and key findings.","page":24,"weight":3},
  {"id":"R070","category":"History","rule":"If DOD occurs during hospital stay, list DOD bullet after the admission bullet.","page":24,"weight":3},

  {"id":"R071","category":"Core Variables","rule":"Capture Date of Diagnosis from pathology 'Collected' date whenever available.","page":25,"weight":5},
  {"id":"R072","category":"Core Variables","rule":"If no pathology, MD‑confirmed imaging date may serve as DOD.","page":25,"weight":5},
  {"id":"R073","category":"Core Variables","rule":"Primary Site comes from pathology addendum if superseded.","page":26,"weight":5},
  {"id":"R074","category":"Core Variables","rule":"Histologic Type is taken from pathology; if unavailable, use MD‑stated clinical type.","page":27,"weight":5},
  {"id":"R075","category":"Core Variables","rule":"Laterality for unifocal tumours resolved via pathology + imaging hierarchy.","page":27,"weight":4},
  {"id":"R076","category":"Core Variables","rule":"Laterality for systemic disease follows MD statement, else ICD‑10 digit.","page":27,"weight":4},
  {"id":"R077","category":"Core Variables","rule":"Stage IV equals metastatic; patient never reverts to non‑metastatic even after response.","page":28,"weight":4},
  {"id":"R078","category":"Core Variables","rule":"Metastatic status NOT captured for haematologic malignancies.","page":28,"weight":4},
  {"id":"R079","category":"Core Variables","rule":"Biomarker list derives from genetic testing **plus** MD note; merge both sources.","page":29,"weight":4},
  {"id":"R080","category":"Core Variables","rule":"Always document pertinent negatives for disease‑specific biomarkers (e.g., EGFR wild‑type).","page":15,"weight":3},
  {"id":"R081","category":"Core Variables","rule":"Surgery events require operative + pathology source, or MD note if others unavailable.","page":29,"weight":4},
  {"id":"R082","category":"Core Variables","rule":"Radiation events prefer Rad‑Onc summary; fallback to Med‑Onc note.","page":30,"weight":3},
  {"id":"R083","category":"Core Variables","rule":"Oral SACT start date hierarchy: MD note > Nurse note > Prescription date.","page":30,"weight":4},
  {"id":"R084","category":"Core Variables","rule":"Injectable SACT dates come from MAR/eMAR; watch for planned vs actual doses.","page":31,"weight":4},
  {"id":"R085","category":"Core Variables","rule":"Clinical‑trial bullets must include protocol number when present.","page":31,"weight":4},
  {"id":"R086","category":"Core Variables","rule":"Every patient entry must include all seven core variables before mark as complete.","page":25,"weight":5},
  {"id":"R087","category":"Core Variables","rule":"Escalate to missing‑info workflow if any core variable cannot be sourced.","page":13,"weight":4},
  {"id":"R088","category":"Core Variables","rule":"Use AJCC/NCCN guidance to decide metastatic status for nodal patterns.","page":28,"weight":4},
  {"id":"R089","category":"Core Variables","rule":"Map ICD‑10 sub‑digit to laterality only when higher evidence absent.","page":27,"weight":3},
  {"id":"R090","category":"Core Variables","rule":"Do not duplicate core‑variable bullets in multiple places; capture once per diagnosis.","page":25,"weight":4},

  {"id":"R091","category":"Multiple Primaries","rule":"When primaries share the same active treatment, combine One‑Liners but keep dual history blocks.","page":16,"weight":4},
  {"id":"R092","category":"Multiple Primaries","rule":"If primaries are in bilateral paired organs, specify Laterality in Disease Header.","page":17,"weight":3},
  {"id":"R093","category":"Multiple Primaries","rule":"Order primary histories by most recent Date of Diagnosis first.","page":16,"weight":4},
  {"id":"R094","category":"Multiple Primaries","rule":"Do not interleave events from different primaries within the same bullet list.","page":16,"weight":4},
  {"id":"R095","category":"Multiple Primaries","rule":"When summarising Brief One‑Liners for multiple primaries, each begins with patient name only once.","page":16,"weight":3},

  {"id":"R096","category":"Metastatic","rule":"Use the word \"Metastatic\" only for Stage IV disease, never for Stage I‑III.","page":15,"weight":3},
  {"id":"R097","category":"Metastatic","rule":"For metastatic progression, phrase \"now with metastasis\" after site.","page":13,"weight":3},
  {"id":"R098","category":"Metastatic","rule":"Do not bold the word 'metastatic' inside imaging summaries.","page":18,"weight":2},
  {"id":"R099","category":"Metastatic","rule":"Recurrence, progression, and metastasis keywords are bolded exactly as spelled—no variations.","page":24,"weight":3},
  {"id":"R100","category":"Metastatic","rule":"If radiologist calls metastasis but MD disagrees, follow MD and remove bolding.","page":24,"weight":3},

  {"id":"R101","category":"Biomarkers","rule":"Breast one‑liners must list ER, PR, HER2, BRCA1/2 status if available.","page":15,"weight":3},
  {"id":"R102","category":"Biomarkers","rule":"Colorectal one‑liners list CEA, MSI/MMR, TMB, APC, NRAS, KRAS when available.","page":15,"weight":3},
  {"id":"R103","category":"Biomarkers","rule":"NSCLC one‑liners list PD‑L1, EGFR, ALK, ROS1.","page":15,"weight":3},
  {"id":"R104","category":"Biomarkers","rule":"Prostate one‑liners list PSA and BRCA2 as applicable.","page":15,"weight":3},
  {"id":"R105","category":"Biomarkers","rule":"When blood‑based biomarker, record vendor, assay, specimen, and findings in one line.","page":19,"weight":3},

  {"id":"R106","category":"Treatment","rule":"Radiation bullets for completed RT include total dose in Gy and total fractions.","page":21,"weight":3},
  {"id":"R107","category":"Treatment","rule":"Current systemic therapy bullets begin with \"Started\" and name regimen.","page":21,"weight":3},
  {"id":"R108","category":"Treatment","rule":"Completed systemic therapy bullets show cycles given and planned.","page":22,"weight":3},
  {"id":"R109","category":"Treatment","rule":"Dose holds indicated with phrase \"Held\" or \"Dose reduced due to X\".","page":22,"weight":3},
  {"id":"R110","category":"Treatment","rule":"Switching drugs inside a regimen is shown with sub‑bullet \"Switched … to … due to X\".","page":22,"weight":3},
  {"id":"R111","category":"Treatment","rule":"Clinical‑trial bullets include start date and, if discontinued, stop reason.","page":22,"weight":3},
  {"id":"R112","category":"Treatment","rule":"Concurrent chemoradiation documented as separate bullets—do not fuse into one line.","page":22,"weight":3},
  {"id":"R113","category":"Treatment","rule":"Surgery bullets embed key pathology findings inside same line where space allows.","page":20,"weight":3},
  {"id":"R114","category":"Treatment","rule":"If surgical margin status is absent, omit field rather than writing 'unknown'.","page":20,"weight":2},
  {"id":"R115","category":"Treatment","rule":"Each treatment bullet starts with the treatment start date (or date range if completed).","page":21,"weight":3},

  {"id":"R116","category":"Follow‑up","rule":"For surveillance > 1 yr, compress imaging into date‑range bullets rather than listing every scan.","page":23,"weight":2},
  {"id":"R117","category":"Recurrence","rule":"Only bold Recurrence/Progression/Metastasis if MD confirms; otherwise record as plain text.","page":24,"weight":3},
  {"id":"R118","category":"Hospitalisation","rule":"Admission bullets summarise presenting complaint, key imaging/lab findings, and outcome.","page":24,"weight":3}
]

import json
import os
import requests
import time
from pyspark.sql import SparkSession
from pyspark.dbutils import DBUtils

# Import your existing prompts
from .helpers import get_precision_recall_prompt
from .helpers import get_correctness_prompt
from .helpers import get_coherence_prompt
from .helpers import get_relevance_prompt
from .helpers import get_completeness_prompt
from .helpers import (
    get_final_correctness_prompt,
    get_final_relevance_prompt,
    get_completeness_final_prompt
)

import json, builtins

builtins.json = json


def call_sonnet(prompt, temperature=0.1, max_tokens=1500):
    """Call Claude Sonnet API with OAuth authentication"""
    print("DEBUG: Starting call_sonnet with OAuth authentication")

    # Get OAuth credentials from environment
    client_id = os.environ.get("DATABRICKS_CLIENT_ID")
    client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
    databricks_host = os.environ.get("DATABRICKS_HOST")

    print(f"DEBUG: DATABRICKS_HOST: {'Found' if databricks_host else 'Not found'}")
    print(f"DEBUG: DATABRICKS_CLIENT_ID: {'Found' if client_id else 'Not found'}")
    print(f"DEBUG: DATABRICKS_CLIENT_SECRET: {'Found' if client_secret else 'Not found'}")

    if not all([client_id, client_secret, databricks_host]):
        missing = []
        if not databricks_host: missing.append("DATABRICKS_HOST")
        if not client_id: missing.append("DATABRICKS_CLIENT_ID")
        if not client_secret: missing.append("DATABRICKS_CLIENT_SECRET")
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    # Remove https:// prefix if it exists
    if databricks_host.startswith("https://"):
        databricks_host = databricks_host[8:]
    elif databricks_host.startswith("http://"):
        databricks_host = databricks_host[7:]

    # Get OAuth token using client credentials
    print("DEBUG: Getting OAuth token...")
    token_url = f"https://{databricks_host}/oidc/v1/token"

    token_data = {
        "grant_type": "client_credentials",
        "scope": "all-apis"
    }

    try:
        token_response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data=token_data,
            timeout=30
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        print("DEBUG: Successfully obtained OAuth token")
    except Exception as e:
        print(f"ERROR: Failed to get OAuth token: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR: Response: {e.response.text}")
        raise RuntimeError(f"OAuth authentication failed: {str(e)}")

    # Now use the token to call the API
    url = f"https://{databricks_host}/serving-endpoints/databricks-claude-3-7-sonnet/invocations"
    print(f"DEBUG: API URL: {url}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    print("DEBUG: Making API request...")
    try:
        import time
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start_time
        print(f"DEBUG: Request completed in {elapsed:.2f} seconds")
        print(f"DEBUG: Response status code: {response.status_code}")

        response.raise_for_status()

    except Exception as e:
        print(f"ERROR: API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR: Response: {e.response.text[:500]}")
        raise RuntimeError(f"API request failed: {str(e)}")

    # Parse response (rest of the function remains the same)
    try:
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]

        # Clean up the content - remove <s> tags and whitespace
        content = content.strip()
        if content.startswith("<s>"):
            content = content[3:]
        if content.endswith("</s>"):
            content = content[:-4]
        content = content.strip()

        # Handle markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()

        # Find the first { and last } to extract just the JSON
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        if first_brace != -1 and last_brace != -1:
            content = content[first_brace:last_brace + 1]

        # Check if it's valid JSON
        if not content.startswith("{"):
            raise ValueError(f"Claude returned non-JSON output:\n{content}")

        return json.loads(content)

    except json.JSONDecodeError as e:
        print("JSON parsing error:")
        print(f"Content to parse: {content[:200]}...")
        raise RuntimeError(f"Failed to parse JSON: {str(e)}")
    except Exception as e:
        print("Claude response could not be parsed.")
        print("Raw response:\n", response.text[:500])
        raise RuntimeError(f"Claude call failed: {str(e)}")


def get_vpp_compliance_prompt(candidate_note):
    """Generate VPP compliance evaluation prompt using rule weights"""

    # Group rules by weight/criticality
    critical_rules = [r for r in VPP_RULES if r['weight'] == 5]
    important_rules = [r for r in VPP_RULES if r['weight'] == 4]
    moderate_rules = [r for r in VPP_RULES if r['weight'] == 3]
    minor_rules = [r for r in VPP_RULES if r['weight'] <= 2]

    # Format rules text
    def format_rules(rules):
        return '\n'.join([f"- {r['id']}: {r['rule']}" for r in rules])

    return f"""
<s> [INST] You are an expert VPP (Virtual Physician Partner) compliance evaluator. Rules have different criticality levels (weights 1-5).

**CANDIDATE NOTE TO EVALUATE:**
{candidate_note}

**VPP RULES BY CRITICALITY:**

**CRITICAL (Weight 5) - MUST PASS:**
{format_rules(critical_rules)}

**IMPORTANT (Weight 4) - SHOULD FOLLOW:**
{format_rules(important_rules)}

**MODERATE (Weight 3) - RECOMMENDED:**
{format_rules(moderate_rules)}

**MINOR (Weight 1-2) - NICE TO HAVE:**
{format_rules(minor_rules)}

**EVALUATION APPROACH:**
- Critical violations (weight 5) significantly impact score
- Important violations (weight 4) moderately impact score  
- Moderate violations (weight 3) noted but don't fail
- Minor violations (weight 1-2) mentioned but minimal impact

**Compliance Levels:**
- **Highly Compliant**: No critical violations, minimal other issues
- **Very Compliant**: No critical violations, some moderate issues ok
- **Moderately Compliant**: 1-2 critical violations OR many important ones
- **Hardly Compliant**: Multiple critical violations
- **Not Compliant**: Major structural failures

Focus on what matters clinically. Minor formatting issues should NOT overshadow good structure.

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no explanatory text.

Return JSON:
{{
  "VPPCompliance": "<Level>",
  "WeightedScore": <calculate 0-100 based on: 100 - (sum of violated rule weights / sum of all weights * 100)>,
  "Explanation": "<Balanced explanation>",
  "ViolationsByWeight": {{
    "Critical": ["List violated rules with weight 5"],
    "Important": ["List violated rules with weight 4"],
    "Moderate": ["List violated rules with weight 3"],
    "Minor": ["List violated rules with weight 1-2"]
  }},
  "ClinicalAssessment": "<Is the note usable despite violations?>"
}}

</s>
"""


def get_unified_pass_fail_prompt(all_metrics, precision_recall):
    """Unified pass/fail prompt with explicit JSON-only instruction"""

    vpp = all_metrics.get('VPPCompliance', {})
    violations = vpp.get('ViolationsByWeight', {})
    critical_count = len(violations.get('Critical', []))
    weighted_score = vpp.get('WeightedScore', 0)

    return f"""
<s> [INST] You are evaluating whether this clinical note passes quality standards, including VPP compliance.

**COMPREHENSIVE METRICS PROVIDED:**

1. **Content Quality Metrics:**
{json.dumps({k: v for k, v in all_metrics.items() if k not in ['VPPCompliance', 'FinalRelevance', 'FinalCompleteness', 'FinalCorrectness']}, indent=2)}

2. **Final Adjusted Scores:**
- Final Relevance: {all_metrics.get('FinalRelevance', {}).get('FinalRelevance', 'N/A')}
- Final Completeness: {all_metrics.get('FinalCompleteness', {}).get('FinalCompleteness', 'N/A')}
- Final Correctness: {all_metrics.get('FinalCorrectness', {}).get('FinalCorrectness', 'N/A')}

3. **VPP Compliance Assessment:**
{json.dumps(vpp, indent=2)}

4. **Precision/Recall Analysis:**
{json.dumps(precision_recall, indent=2)}

**INTEGRATED PASS CRITERIA (ALL must be met):**
- NO critical VPP violations (weight 5) - this is mandatory for VPP use
- Weighted VPP score ≥ 70%
- All final content metrics ≥ "Neutral"
- No critical missing information that affects patient care
- Note is clinically safe and usable

**ACCEPTABLE ISSUES:**
- Minor formatting violations (weight 1-2)
- Some moderate violations if core structure intact
- Minor missing non-critical details
- Stylistic preferences

**FAIL CRITERIA (ANY triggers fail):**
- Critical VPP violations present
- Weighted VPP score < 70%
- Any final content metric < "Neutral"
- Critical information missing (diagnoses, treatments, etc.)
- Note is clinically unsafe

**Overall Quality Scale:**
- 5: Excellent (minimal issues, VPP score 90%+)
- 4: Good (minor issues only, VPP score 80-89%)
- 3: Acceptable (notable but non-critical issues, VPP score 70-79%)
- 2: Poor (significant problems, VPP score 60-69%)
- 1: Failing (critical issues, VPP score <60%)

CRITICAL INSTRUCTION: Return ONLY valid JSON with no additional text, no markdown formatting, and no code blocks. The response must start with {{ and end with }}.

Return this exact JSON structure:
{{
  "OverallRating": <1-5>,
  "PassFail": "<Pass or Fail>",
  "UnifiedExplanation": "<Comprehensive assessment integrating all dimensions>",
  "ContentQualitySummary": "<Brief summary of content metrics>",
  "VPPComplianceSummary": "<Brief summary of VPP adherence>",
  "FactualAccuracySummary": "<Brief summary of precision/recall>",
  "KeyStrengths": ["<What the note does well>"],
  "CriticalIssues": ["<Only issues affecting clinical use or critical VPP violations>"],
  "MinorIssues": ["<Non-critical improvements>"],
  "ClinicalUsability": "<Is this safe for patient care? Yes/No with reason>",
  "RecommendationPriority": ["<Top 3 fixes in order of importance>"]
}}

</s>
"""


def evaluate_unified_pass_fail(all_metrics, precision_recall):
    """Unified pass/fail evaluation that includes all dimensions"""
    try:
        prompt = get_unified_pass_fail_prompt(all_metrics, precision_recall)
        result = call_sonnet(prompt, temperature=0.1, max_tokens=1500)
        return result
    except Exception as e:
        return {
            "OverallRating": "N/A",
            "PassFail": "Error",
            "UnifiedExplanation": f"Evaluation failed: {str(e)}",
            "CriticalIssues": ["System error during evaluation"]
        }


def evaluate_row_with_unified_reporting(md_note, candidate_note):
    """Complete evaluation with unified reporting including VPP compliance"""
    results = {}

    try:
        print("Step 1/7: Running precision/recall analysis...")
        pr_result = call_sonnet(get_precision_recall_prompt(md_note, md_note, candidate_note))
        results['PrecisionRecall'] = pr_result

        print("Step 2/7: Evaluating relevance...")
        relevance = call_sonnet(get_relevance_prompt(md_note, candidate_note))
        results['Relevance'] = relevance

        print("Step 3/7: Evaluating coherence...")
        coherence = call_sonnet(get_coherence_prompt(md_note, candidate_note))
        results['Coherence'] = coherence

        print("Step 4/7: Evaluating completeness...")
        completeness = call_sonnet(get_completeness_prompt(md_note, candidate_note))
        results['Completeness'] = completeness

        print("Step 5/7: Evaluating correctness...")
        correctness = call_sonnet(get_correctness_prompt(md_note, candidate_note))
        results['Correctness'] = correctness

        print("Step 6/7: Evaluating VPP compliance...")
        vpp_compliance = call_sonnet(get_vpp_compliance_prompt(candidate_note))
        results['VPPCompliance'] = vpp_compliance

        print("Step 7/7: Computing final scores and unified assessment...")

        # Get final adjusted scores
        final_relevance = call_sonnet(get_final_relevance_prompt(relevance, pr_result))
        final_completeness = call_sonnet(get_completeness_final_prompt(completeness, pr_result))
        final_correctness = call_sonnet(get_final_correctness_prompt(correctness, pr_result))

        results['FinalRelevance'] = final_relevance
        results['FinalCompleteness'] = final_completeness
        results['FinalCorrectness'] = final_correctness

        # Create all_metrics for unified evaluation
        all_metrics = {
            'Relevance': relevance,
            'Coherence': coherence,
            'Completeness': completeness,
            'Correctness': correctness,
            'FinalRelevance': final_relevance,
            'FinalCompleteness': final_completeness,
            'FinalCorrectness': final_correctness,
            'VPPCompliance': vpp_compliance
        }

        # Get unified pass/fail assessment
        unified_pass_fail = evaluate_unified_pass_fail(all_metrics, pr_result)
        results['UnifiedPassFail'] = unified_pass_fail

        # Create summary
        results['Summary'] = {
            "OverallRating": unified_pass_fail.get("OverallRating", "N/A"),
            "PassFail": unified_pass_fail.get("PassFail", "N/A"),
            "WeightedVPPScore": f"{vpp_compliance.get('WeightedScore', 'N/A')}%",
            "VPPCompliance": vpp_compliance.get('VPPCompliance', 'N/A'),
            "ContentQuality": {
                "Relevance": relevance.get('Relevance', 'N/A'),
                "Coherence": coherence.get('Coherence', 'N/A'),
                "Completeness": completeness.get('Completeness', 'N/A'),
                "Correctness": correctness.get('Correctness', 'N/A')
            },
            "FinalScores": {
                "FinalRelevance": final_relevance.get('FinalRelevance', 'N/A'),
                "FinalCompleteness": final_completeness.get('FinalCompleteness', 'N/A'),
                "FinalCorrectness": final_correctness.get('FinalCorrectness', 'N/A')
            }
        }

        return results

    except Exception as e:
        results["error"] = str(e)
        return results


def display_unified_results(result):
    """Display comprehensive unified evaluation results"""

    print("\n" + "=" * 70)
    print("COMPREHENSIVE VPP EVALUATION REPORT")
    print("=" * 70)

    # Overall verdict
    unified = result.get("UnifiedPassFail", {})
    summary = result.get("Summary", {})

    print(f"\n🎯 OVERALL RATING: {unified.get('OverallRating', 'N/A')}/5")
    print(f"📋 FINAL DECISION: {unified.get('PassFail', 'N/A')}")

    # VPP Compliance Section
    print(f"\n" + "-" * 50)
    print("VPP COMPLIANCE ASSESSMENT")
    print("-" * 50)
    vpp = result.get("VPPCompliance", {})
    print(f"Compliance Level: {vpp.get('VPPCompliance', 'N/A')}")
    print(f"Weighted Score: {vpp.get('WeightedScore', 'N/A')}%")
    print(f"Clinical Usability: {vpp.get('ClinicalAssessment', 'N/A')}")

    violations = vpp.get('ViolationsByWeight', {})
    critical = violations.get('Critical', [])
    if critical:
        print(f"\n🚨 CRITICAL VIOLATIONS:")
        for v in critical:
            print(f"   • {v}")
    else:
        print(f"\n✅ No critical VPP violations")

    # Content Quality Section
    print(f"\n" + "-" * 50)
    print("CONTENT QUALITY METRICS")
    print("-" * 50)
    content = summary.get('ContentQuality', {})
    final_scores = summary.get('FinalScores', {})

    print("\nInitial Assessments:")
    for metric, value in content.items():
        print(f"  • {metric}: {value}")

    print("\nFinal Adjusted Scores:")
    for metric, value in final_scores.items():
        print(f"  • {metric}: {value}")

    # Precision/Recall Section
    print(f"\n" + "-" * 50)
    print("FACTUAL ACCURACY ANALYSIS")
    print("-" * 50)
    pr = result.get("PrecisionRecall", {})
    missing = pr.get('MissingFields', [])
    spurious = pr.get('SpuriousFields', [])

    if missing:
        print(f"❌ Missing Fields ({len(missing)}):")
        for field in missing[:3]:  # Show first 3
            print(f"   • {field}")
        if len(missing) > 3:
            print(f"   • ... and {len(missing) - 3} more")
    else:
        print("✅ No missing fields detected")

    if spurious:
        print(f"\n➕ Spurious Fields ({len(spurious)}):")
        for field in spurious[:3]:  # Show first 3
            print(f"   • {field}")
        if len(spurious) > 3:
            print(f"   • ... and {len(spurious) - 3} more")
    else:
        print("✅ No spurious fields detected")

    # Clinical Assessment
    print(f"\n" + "-" * 50)
    print("CLINICAL ASSESSMENT")
    print("-" * 50)
    print(f"Safe for Patient Care: {unified.get('ClinicalUsability', 'N/A')}")

    # Strengths and Issues
    if unified.get('KeyStrengths'):
        print(f"\n💪 KEY STRENGTHS:")
        for strength in unified.get('KeyStrengths', []):
            print(f"   • {strength}")

    if unified.get('CriticalIssues'):
        print(f"\n❗ CRITICAL ISSUES:")
        for issue in unified.get('CriticalIssues', []):
            print(f"   • {issue}")

    # Recommendations
    print(f"\n" + "-" * 50)
    print("PRIORITY RECOMMENDATIONS")
    print("-" * 50)
    for i, rec in enumerate(unified.get('RecommendationPriority', []), 1):
        print(f"{i}. {rec}")

    # Final Summary
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(unified.get('UnifiedExplanation', 'No explanation available'))

    return result


