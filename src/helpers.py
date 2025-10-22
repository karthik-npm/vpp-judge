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

def get_final_relevance_prompt(relevance_evaluation, precision_recall_result):
    spurious_fields = precision_recall_result.get("SpuriousFields", [])

    return f"""
<s> [INST] You are an expert in clinical note evaluation. Your goal is to assign a **Final Relevance** rating that reflects how well the candidate note stays within the scope of facts present in the original MD note, and to grade the **clinical criticality** of any **spurious fields** that were introduced.

You are provided with:
- A subjective relevance evaluation:
{json.dumps(relevance_evaluation, indent=2)}

- A precision/recall analysis listing **spurious fields** (present in the candidate note but **absent** from the original MD note):
Spurious Fields: {spurious_fields}

**Criticality rubric (apply to EACH spurious item):**
- **Critical** (weight 3): Stage/TNM or metastatic status (e.g., "Metastatic", "Stage IV", "progression", "recurrence"); primary diagnosis/site/laterality; histology/grade; management‑changing biomarkers (e.g., ER/PR/HER2; EGFR/ALK/ROS1/PD‑L1; MSI/MMR; BRCA1/2); delivered systemic therapy starts/stops/regimen changes; radiation dose/fractions; surgery with margins/nodes; Date of Diagnosis (DOD) when used as a core variable.
- **Important** (weight 2): Imaging/labs that inform but do not alter stage; cycle counts; dose holds/reductions; clinically meaningful adverse effects tied to management; explicit follow‑up/surveillance plans with modality/timing.
- **Minor** (weight 1): Vitals; ROS; social/family history; administrative/scheduling/billing; generic education; narrative prose that adds no clinical facts.

**Scoring rules for Final Relevance (combine subjective rating with penalties from spurious items):**
- If ANY **Critical** spurious item exists → cap **Final Relevance** at **"Hardly"**.
- If **no Critical** but **>2 Important** items → cap at **"Neutral"**.
- If **only Minor** items:
  • 1–3 items → at most **"Very"** (do not reduce below the subjective rating if it was already "Very"/"Highly").
  • ≥4 items → cap at **"Neutral"**.
- If **no spurious** items → Final Relevance may equal the subjective rating.

Return **JSON ONLY**:
{{
  "FinalRelevance": "<Almost not at all|Hardly|Neutral|Very|Highly>",
  "Explanation": "One concise sentence referencing criticality and counts.",
  "SpuriousCriticality": {{
    "Counts": {{"critical": <int>, "important": <int>, "minor": <int>}},
    "Items": [
      {{"text":"<spurious item>",
        "category":"<stage|diagnosis|treatment|radiation|surgery|biomarker|imaging|follow_up|admin|social|vitals|other>",
        "criticality":"<critical|important|minor>",
        "reason":"<why this level>"}}
    ],
    "WeightedPenalty": <int>,  # critical=3, important=2, minor=1
    "RuleApplied": "<which cap/logic determined the final rating>"
  }}
}}

CRITICAL: Output MUST be valid JSON only. No markdown/code fences or extra text. [/INST]</s>
"""


def get_completeness_final_prompt(completeness_evaluation, precision_recall_result):
    missing_fields = precision_recall_result.get("MissingFields", [])

    return f"""
<s> [INST] You are an expert in clinical note evaluation. Assign the **Final Completeness** rating (did the candidate preserve all important information from the original MD note?) and grade the **clinical criticality** of any missing items.

You are provided with:
- A subjective completeness evaluation:
{json.dumps(completeness_evaluation, indent=2)}

- A precision/recall analysis listing **fields from the original that are missing** in the candidate:
Missing Fields: {missing_fields}

**Criticality rubric (for EACH missing item):**
- **Critical** (weight 3): Date of Diagnosis (DOD) and core variables (primary site/laterality, histology/grade, Stage/TNM, metastatic status); confirmed recurrence/progression/metastasis; surgery with margins/nodes; delivered systemic therapy (start/stop/regimen) and pivotal reasons for change; radiation delivered (dose Gy, fractions, start/stop); management‑changing biomarkers (ER/PR/HER2; EGFR/ALK/ROS1/PD‑L1; MSI/MMR; BRCA1/2; etc.).
- **Important** (weight 2): Imaging/labs that inform but do not alter stage; cycle counts; dose holds/reductions; significant adverse effects relevant to management; explicit follow‑up/surveillance plans (modality + timing).
- **Minor** (weight 1): Vitals; ROS; social/family history; administrative/scheduling/billing; generic counseling; non‑actionable negatives.

**Scoring rules for Final Completeness:**
- Any **Critical** missing item → Final Completeness ≤ **"Hardly"**.
- If **no Critical** but **>2 Important** missing → Final Completeness ≤ **"Neutral"**.
- Only **Minor** missing:
  • ≤3 items → may be **"Very"** or **"Highly"** (depending on how fully the core clinical story is preserved).
  • ≥4 items → **"Very"** at most.
- If **nothing material** is missing → **"Highly"**.

**Guardrails**
- Spurious or irrelevant additions **do not** affect completeness (that's handled by relevance/precision).
- Prefer **delivered** care over planned; planned items do not count as missing if delivered equivalents are present.
- Treat semantically equivalent phrasing as present (don't penalize wording differences).

Return **JSON ONLY**:
{{
  "FinalCompleteness": "<Almost not at all|Hardly|Neutral|Very|Highly>",
  "Explanation": "Brief justification referencing criticality counts.",
  "MissingCriticality": {{
    "Counts": {{"critical": <int>, "important": <int>, "minor": <int>}},
    "Items": [
      {{"text":"<missing item>",
        "category":"<stage|diagnosis|treatment|surgery|radiation|biomarker|imaging|follow_up|admin|social|vitals|other>",
        "criticality":"<critical|important|minor>",
        "reason":"<why this level>"}}
    ],
    "WeightedMissing": <int>  # critical=3, important=2, minor=1
  }}
}}

Please output **only** valid JSON; no code fences or extra prose. [/INST]</s>
"""


def get_final_correctness_prompt(correctness_evaluation, precision_recall_result):
    spurious_fields = precision_recall_result.get("SpuriousFields", [])
    precision_score = precision_recall_result.get("Precision", "")

    return f"""
<s> [INST] You are an expert in clinical documentation evaluation. Assign the **Final Correctness** rating (are values/facts correct vs. the original MD note?) and grade the **clinical criticality** of any **spurious** or **incorrect/mismatched** items.

You are provided with:
- A **subjective correctness evaluation** that may include a list like "InaccurateFields":
{json.dumps(correctness_evaluation, indent=2)}

- A **precision/recall analysis**:
Precision (Likert): {precision_score}
Spurious Fields: {spurious_fields}

**What to analyze**
- Treat each item in "InaccurateFields" (if present) as a **mismatch**.
- Treat each item in "SpuriousFields" as **spurious**.
- For each item (mismatch or spurious), assign a **category** and **criticality** using the rubric below.

**Criticality rubric (for EACH item):**
- **Critical** (weight 3): Stage/TNM or metastatic status; primary diagnosis/site/laterality; histology/grade; management‑changing biomarkers; delivered systemic therapy starts/stops/regimen changes; radiation dose/fractions; surgery margins/nodes; DOD core variable.
- **Important** (weight 2): Imaging/labs that inform but do not alter stage; cycle counts; dose holds/reductions; significant adverse effects; explicit follow‑up/surveillance plans.
- **Minor** (weight 1): Vitals; ROS; social/family history; administrative/billing; generic counseling; narrative filler.

**Caps for Final Correctness (apply the strongest cap that matches):**
1) If **any Critical** item (spurious or mismatch) → Final Correctness ≤ **"Hardly"**.
2) Else if **>2 Important** items → Final Correctness ≤ **"Neutral"**.
3) Else if Precision Likert is **not** "Very High" or "High" → Final Correctness ≤ **"Neutral"**.
4) Else (no critical/important errors and high precision): may reflect the subjective rating (e.g., "Very"/"Highly").

Return **JSON ONLY**:
{{
  "FinalCorrectness": "<Almost not at all|Hardly|Neutral|Very|Highly>",
  "Explanation": "One concise sentence referencing precision and criticality counts.",
  "ErrorCriticality": {{
    "Counts": {{"critical": <int>, "important": <int>, "minor": <int>}},
    "Items": [
      {{"text":"<field>",
        "type":"<spurious|mismatch>",
        "category":"<stage|diagnosis|treatment|radiation|surgery|biomarker|imaging|follow_up|admin|social|vitals|other>",
        "criticality":"<critical|important|minor>",
        "reason":"<why this level>"}}
    ],
    "WeightedPenalty": <int>,  # critical=3, important=2, minor=1
    "RuleApplied": "<which cap/logic determined the final rating>"
  }}
}}

CRITICAL: Output must be valid JSON only (no markdown, no code fences). [/INST]</s>
"""


def get_precision_recall_prompt(nl_query, gold_summary, model_summary):
    # Generates a precision/recall prompt adapted to MD → VPP note restoration
    return f"""
<s> [INST] You are an expert in clinical documentation evaluation.

The original medical note written by a physician is as follows:
{nl_query}

This is the reference note, and we will treat it as the ground truth.

Now, here is the final note that was generated by a model and then passed through a correction system to remove spurious information:
{model_summary}

Your task is to compare this final note to the original physician-authored note and evaluate whether it faithfully retains the correct information and excludes hallucinated or spurious additions.

**Definitions:**
- Fields are **missing** if they appear in the original (gold) note but are **absent** from the final note.
- Fields are **spurious** if they appear in the final note but **do not exist** in the original physician-authored note.
- Consider "mismatch" cases (changed values) as **spurious** for the purposes of precision.

A "field" is any medically relevant unit of information — meds, dosages, test results, diagnoses, procedures, dates/ranges, staging, biomarkers, radiology conclusions, etc.

Be strict in your comparisons. Semantically equivalent language is acceptable **only if the facts match**.

---

### Evaluation Guidelines

Use the following **Likert scale for Precision**:
- **Very High**: No spurious fields
- **High**: No spurious fields
- **Medium**: At most one spurious field
- **Slightly low**: One to two spurious fields
- **Very low**: More than two spurious fields

Use the following **Likert scale for Recall**:
- **Very High**: No missing fields
- **High**: No missing fields
- **Medium**: At most one missing field
- **Slightly low**: One to two missing fields
- **Very low**: More than two missing fields

**Criticality rubric (apply to EACH missing or spurious item):**
- **Critical** (weight 3): Stage/TNM or metastatic status; primary diagnosis/site/laterality; histology/grade; management‑changing biomarkers; delivered systemic therapy start/stop/regimen changes; radiation dose/fractions; surgery margins/nodes; DOD.
- **Important** (weight 2): Imaging/labs that inform but do not alter stage; cycle counts; dose holds/reductions; significant adverse effects; explicit follow‑up/surveillance plans.
- **Minor** (weight 1): Vitals; ROS; social/family history; administrative/scheduling; generic counseling.

---

Return your evaluation in **JSON ONLY** with BOTH simple lists and detailed classification:

{{
  "Precision": "<Likert>",
  "Recall": "<Likert>",
  "MissingFields": ["<plain list of missing fields>"],
  "SpuriousFields": ["<plain list of spurious fields>"],
  "MissingFieldsDetailed": [
    {{"text":"<missing item>",
      "category":"<stage|diagnosis|treatment|surgery|radiation|biomarker|imaging|follow_up|admin|social|vitals|other>",
      "criticality":"<critical|important|minor>",
      "reason":"<why this level>"}}
  ],
  "SpuriousFieldsDetailed": [
    {{"text":"<spurious item>",
      "category":"<stage|diagnosis|treatment|radiation|surgery|biomarker|imaging|follow_up|admin|social|vitals|other>",
      "criticality":"<critical|important|minor>",
      "reason":"<why this level>"}}
  ],
  "WeightedMissing": <int>,   # sum weights (critical=3, important=2, minor=1)
  "WeightedSpurious": <int>   # sum weights (critical=3, important=2, minor=1)
}}

Constraints:
- Output **only** valid JSON; no markdown or code fences.
- Keep items concise and clinically scoped. [/INST]</s>
"""


def get_coherence_prompt(original_md_note, candidate_note):
    return f"""
<s> [INST] You are an expert in clinical summarization evaluation.

The following is a note originally written by a medical doctor:
{original_md_note}

Below is a note that was derived from an LLM-generated summary, then passed through a correction system:
{candidate_note}

Your task is to evaluate the **Coherence** of the corrected note.

**Coherence** refers to the logical flow and structural clarity of the document:
- Are the sentences well-ordered?
- Do transitions between topics make sense?
- Is it easy to follow from start to end?

You are **not** judging factual accuracy or missing/spurious content. This is **purely** about the **readability and structure** of the candidate.

---

### Likert Scale for Coherence

- **Almost not at all**: Sentences are disjointed or unrelated. The flow is broken or hard to follow.
- **Hardly**: Some logical structure exists, but transitions are awkward or the ordering is confusing.
- **Neutral**: The structure is acceptable but not smooth. Some sections feel disconnected.
- **Very**: The flow is mostly logical, with only minor rough spots in transitions.
- **Highly**: The entire note is smoothly structured, easy to follow, and logically ordered.

---

### Your Task

Provide your **Coherence** rating for the candidate note in this JSON format:

{{
  "Coherence": "<almost not at all|hardly|neutral|very|highly>",
  "Explanation": "One or two sentences about flow/organization only."
}}

Please DO NOT generate any text other than this JSON.
No markdown/code fences; the result must be loadable via `json.loads()`. [/INST]</s>
"""


def get_completeness_prompt(original_md_note, candidate_note):
    return f"""
<s> [INST] You are an expert in clinical summarization evaluation.

You will rate **Completeness** (did the candidate preserve all important information from the original MD note?) **and** grade the **clinical criticality** of any missing items.

ORIGINAL PHYSICIAN NOTE:
{original_md_note}

CANDIDATE NOTE:
{candidate_note}

**What to do**
1) Identify concrete **missing items** (present in the original, absent or materially less specific in the candidate).
2) For each missing item, assign a **category** and **criticality** using the rubric below.
3) Decide a **Completeness** Likert rating using the caps under "Scoring rules".
4) Return JSON only.

**Criticality rubric (for EACH missing item):**
- **Critical** (weight 3): DOD and core variables (primary site/laterality, histology/grade, Stage/TNM, metastatic status); confirmed recurrence/progression/metastasis; surgery with margins/nodes; delivered systemic therapy (start/stop/regimen) and pivotal reasons for change; radiation delivered (dose Gy, fractions, start/stop); management‑changing biomarkers (ER/PR/HER2; EGFR/ALK/ROS1/PD‑L1; MSI/MMR; BRCA1/2; etc.).
- **Important** (weight 2): Imaging/labs that inform but do not alter stage; cycle counts; dose holds/reductions; significant adverse effects relevant to management; explicit follow‑up/surveillance plans (modality + timing).
- **Minor** (weight 1): Vitals; ROS; social/family history; administrative/scheduling/billing; generic counseling; non‑actionable negatives.

**Scoring rules for Completeness:**
- Any **Critical** missing item → Completeness ≤ **"hardly"**.
- If **no Critical** but **>2 Important** missing → Completeness ≤ **"neutral"**.
- Only **Minor** missing:
  • ≤3 items → may be **"very"** or **"highly"** (depending on how fully the core clinical story is preserved).
  • ≥4 items → **"very"** at most.
- If **nothing material** is missing → **"highly"**.

**Guardrails**
- Spurious/irrelevant additions **do not** affect completeness (that's relevance/precision).
- Prefer **delivered** care over planned; planned items do not count as missing if delivered equivalents are present.
- Treat semantically equivalent phrasing as present (don't penalize wording differences).

Return **JSON ONLY**:
{{
  "Completeness": "<almost not at all|hardly|neutral|very|highly>",
  "Explanation": "Brief justification referencing criticality counts.",
  "MissingAnalysis": {{
    "Counts": {{"critical": <int>, "important": <int>, "minor": <int>}},
    "Items": [
      {{"text":"<missing item>",
        "category":"<stage|diagnosis|treatment|surgery|radiation|biomarker|imaging|follow_up|admin|social|vitals|other>",
        "criticality":"<critical|important|minor>",
        "reason":"<why this level>"}}
    ],
    "WeightedMissing": <int>  # critical=3, important=2, minor=1
  }}
}}

Please output **only** valid JSON; no code fences or extra prose. [/INST]</s>
"""


def get_precision_recall_prompt(nl_query, gold_summary, model_summary):
    # Generates a precision/recall prompt adapted to MD → VPP note restoration
    return f"""
<s> [INST] You are an expert in clinical documentation evaluation.

The original medical note written by a physician is as follows:
{nl_query}

This is the reference note, and we will treat it as the ground truth.

Now, here is the final note that was generated by a model and then passed through a correction system to remove spurious information:
{model_summary}

Your task is to compare this final note to the original physician-authored note and evaluate whether it faithfully retains the correct information and excludes hallucinated or spurious additions.

**Definitions:**
- Fields are **missing** if they appear in the original (gold) note but are **absent** from the final note.
- Fields are **spurious** if they appear in the final note but **do not exist** in the original physician-authored note.
- Consider "mismatch" cases (changed values) as **spurious** for the purposes of precision.

A "field" is any medically relevant unit of information — meds, dosages, test results, diagnoses, procedures, dates/ranges, staging, biomarkers, radiology conclusions, etc.

Be strict in your comparisons. Semantically equivalent language is acceptable **only if the facts match**.

---

### Example 1: Perfect Precision and Recall

#### MD Note:
"Patient with stage IIIA lung adenocarcinoma. EGFR negative. Started carboplatin/pemetrexed 03/15/2021."

#### Final Note:
"Patient with stage IIIA lung adenocarcinoma. EGFR negative. Started carboplatin/pemetrexed on March 15, 2021."

#### Evaluation:
{{
  "Precision": "Very High",
  "Recall": "Very High",
  "MissingFields": [],
  "SpuriousFields": [],
  "MissingFieldsDetailed": [],
  "SpuriousFieldsDetailed": [],
  "WeightedMissing": 0,
  "WeightedSpurious": 0
}}

---

### Example 2: Missing Critical Information

#### MD Note:
"Breast cancer, ER/PR positive, HER2 negative. Stage IIB. Started letrozole 06/02/2021."

#### Final Note:
"Breast cancer. Started letrozole in June 2021."

#### Evaluation:
{{
  "Precision": "Very High",
  "Recall": "Very low",
  "MissingFields": ["ER/PR positive", "HER2 negative", "Stage IIB"],
  "SpuriousFields": [],
  "MissingFieldsDetailed": [
    {{"text": "ER/PR positive", "category": "biomarker", "criticality": "critical", "reason": "Management-changing receptor status"}},
    {{"text": "HER2 negative", "category": "biomarker", "criticality": "critical", "reason": "Key biomarker for treatment selection"}},
    {{"text": "Stage IIB", "category": "stage", "criticality": "critical", "reason": "TNM staging is essential clinical information"}}
  ],
  "SpuriousFieldsDetailed": [],
  "WeightedMissing": 9,
  "WeightedSpurious": 0
}}

---

### Example 3: Spurious Critical Addition

#### MD Note:
"PSA 0.3. Continue Lupron. Follow-up 3 months."

#### Final Note:
"PSA 0.3. Bone scan shows new metastases. Continue Lupron. Follow-up 3 months."

#### Evaluation:
{{
  "Precision": "Slightly low",
  "Recall": "Very High",
  "MissingFields": [],
  "SpuriousFields": ["Bone scan shows new metastases"],
  "MissingFieldsDetailed": [],
  "SpuriousFieldsDetailed": [
    {{"text": "Bone scan shows new metastases", "category": "imaging", "criticality": "critical", "reason": "False metastatic progression changes staging/management"}}
  ],
  "WeightedMissing": 0,
  "WeightedSpurious": 3
}}

---

### Example 4: Mixed Minor Issues

#### MD Note:
"Follow-up visit. CBC normal. Vital signs stable. Continue current regimen."

#### Final Note:
"Follow-up visit. Continue current regimen. Patient counseled on diet."

#### Evaluation:
{{
  "Precision": "Slightly low",
  "Recall": "Slightly low",
  "MissingFields": ["CBC normal", "Vital signs stable"],
  "SpuriousFields": ["Patient counseled on diet"],
  "MissingFieldsDetailed": [
    {{"text": "CBC normal", "category": "imaging", "criticality": "minor", "reason": "Routine lab without specific values"}},
    {{"text": "Vital signs stable", "category": "vitals", "criticality": "minor", "reason": "Non-specific vital sign mention"}}
  ],
  "SpuriousFieldsDetailed": [
    {{"text": "Patient counseled on diet", "category": "admin", "criticality": "minor", "reason": "Generic counseling addition"}}
  ],
  "WeightedMissing": 2,
  "WeightedSpurious": 1
}}

---

### Evaluation Guidelines

Use the following **Likert scale for Precision**:
- **Very High**: No spurious fields
- **High**: No spurious fields
- **Medium**: At most one spurious field
- **Slightly low**: One to two spurious fields
- **Very low**: More than two spurious fields

Use the following **Likert scale for Recall**:
- **Very High**: No missing fields
- **High**: No missing fields
- **Medium**: At most one missing field
- **Slightly low**: One to two missing fields
- **Very low**: More than two missing fields

**Criticality rubric (apply to EACH missing or spurious item):**
- **Critical** (weight 3): Stage/TNM or metastatic status; primary diagnosis/site/laterality; histology/grade; management‑changing biomarkers; delivered systemic therapy start/stop/regimen changes; radiation dose/fractions; surgery margins/nodes; DOD.
- **Important** (weight 2): Imaging/labs that inform but do not alter stage; cycle counts; dose holds/reductions; significant adverse effects; explicit follow‑up/surveillance plans.
- **Minor** (weight 1): Vitals; ROS; social/family history; administrative/scheduling; generic counseling.

---

Return your evaluation in **JSON ONLY** with BOTH simple lists and detailed classification:

{{
  "Precision": "<Likert>",
  "Recall": "<Likert>",
  "MissingFields": ["<plain list of missing fields>"],
  "SpuriousFields": ["<plain list of spurious fields>"],
  "MissingFieldsDetailed": [
    {{"text":"<missing item>",
      "category":"<stage|diagnosis|treatment|surgery|radiation|biomarker|imaging|follow_up|admin|social|vitals|other>",
      "criticality":"<critical|important|minor>",
      "reason":"<why this level>"}}
  ],
  "SpuriousFieldsDetailed": [
    {{"text":"<spurious item>",
      "category":"<stage|diagnosis|treatment|radiation|surgery|biomarker|imaging|follow_up|admin|social|vitals|other>",
      "criticality":"<critical|important|minor>",
      "reason":"<why this level>"}}
  ],
  "WeightedMissing": <int>,   # sum weights (critical=3, important=2, minor=1)
  "WeightedSpurious": <int>   # sum weights (critical=3, important=2, minor=1)
}}

Constraints:
- Output **only** valid JSON; no markdown or code fences.
- Keep items concise and clinically scoped. [/INST]</s>
"""

def get_relevance_prompt(original_md_note, candidate_note):
    return f"""
<s> [INST] You are an expert in clinical summarization evaluation.

The following is a note originally written by a medical doctor:
{original_md_note}

Below is a note that was generated by a model and later corrected:
{candidate_note}

Your task is to evaluate the **Relevance** of the corrected note and grade the **clinical criticality** of any irrelevant content.

Relevance means: does the candidate note stay focused on content from the original physician-authored note? Does it include **only medically relevant information** derived from that note, without introducing unrelated, unnecessary, or speculative content?

You are NOT judging whether it includes everything (that's **Completeness**) or whether values are right (that's **Correctness**). You are judging whether included content is **on-topic** and **faithful to the intent of the original MD note**.

---

### Likert Scale for Relevance

- **Almost not at all**: The candidate is filled with irrelevant or fabricated content, barely related to the MD note.
- **Hardly**: It touches on a few original ideas, but most of the note is tangential or off-topic.
- **Neutral**: The candidate contains some real content from the MD note, but also drifts with loosely related or speculative info.
- **Very**: The candidate includes mostly relevant content from the MD note with minor irrelevancies.
- **Highly**: The candidate includes only information found in or directly derivable from the MD note — no extra content.

**Criticality rubric (for EACH irrelevant/spurious item):**
- **Critical** (weight 3): False staging/TNM or metastatic status; incorrect primary diagnosis/site/laterality; spurious histology/grade; fabricated management-changing biomarkers; false systemic therapy changes; spurious radiation; fabricated surgery details; incorrect DOD.
- **Important** (weight 2): Spurious imaging/labs that would inform staging; fabricated cycle counts; false dose modifications; spurious adverse effects; fabricated follow-up plans.
- **Minor** (weight 1): Irrelevant vitals; unrelated ROS; spurious social/family history; unnecessary administrative content; generic counseling not in original.

---

### Example: Oncology Note with Critical Irrelevance

#### MD Note:
"Follow-up for lung cancer. CT stable. Continue pembrolizumab."

#### Candidate Note:
"Follow-up for Stage IV lung cancer with brain metastases. CT stable. EGFR positive. Continue pembrolizumab. Started prophylactic anticonvulsants."

#### Evaluation:
{{
  "Relevance": "hardly",
  "Explanation": "Critical fabrications of staging, metastases, and biomarker status not present in original.",
  "IrrelevantContent": ["Stage IV", "brain metastases", "EGFR positive", "prophylactic anticonvulsants"],
  "IrrelevantContentDetailed": [
    {{"text": "Stage IV", "category": "stage", "criticality": "critical", "reason": "False staging information"}},
    {{"text": "brain metastases", "category": "diagnosis", "criticality": "critical", "reason": "Fabricated metastatic disease"}},
    {{"text": "EGFR positive", "category": "biomarker", "criticality": "critical", "reason": "False biomarker status affects treatment"}},
    {{"text": "prophylactic anticonvulsants", "category": "treatment", "criticality": "important", "reason": "Spurious medication addition"}}
  ],
  "WeightedIrrelevance": 11
}}

---

Return your evaluation in **JSON ONLY**:

{{
  "Relevance": "<almost not at all|hardly|neutral|very|highly>",
  "Explanation": "Brief explanation of relevance to original note.",
  "IrrelevantContent": ["<list of content not derived from original>"],
  "IrrelevantContentDetailed": [
    {{"text": "<irrelevant item>",
      "category": "<stage|diagnosis|treatment|radiation|surgery|biomarker|imaging|follow_up|admin|social|vitals|other>",
      "criticality": "<critical|important|minor>",
      "reason": "<why this level>"}}
  ],
  "WeightedIrrelevance": <int>  # sum weights (critical=3, important=2, minor=1)
}}

Please DO NOT generate any text other than this JSON.
No markdown/code fences; the result must be loadable with `json.loads()`. [/INST]</s>
"""

def get_coherence_prompt(original_md_note, candidate_note):
    return f"""
<s> [INST] You are an expert in clinical summarization evaluation.

The following is a note originally written by a medical doctor:
{original_md_note}

Below is a note that was derived from an LLM-generated summary, then passed through a correction system:
{candidate_note}

Your task is to evaluate the **Coherence** of the corrected note.

**Coherence** refers to the logical flow and structural clarity of the document:
- Are the sentences well-ordered?
- Do transitions between topics make sense?
- Is it easy to follow from start to end?

You are **not** judging factual accuracy or missing/spurious content. This is **purely** about the **readability and structure** of the candidate.

---

### Likert Scale for Coherence

- **Almost not at all**: Sentences are disjointed or unrelated. The flow is broken or hard to follow.
- **Hardly**: Some logical structure exists, but transitions are awkward or the ordering is confusing.
- **Neutral**: The structure is acceptable but not smooth. Some sections feel disconnected.
- **Very**: The flow is mostly logical, with only minor rough spots in transitions.
- **Highly**: The entire note is smoothly structured, easy to follow, and logically ordered.

---

### Your Task

Provide your **Coherence** rating for the candidate note in this JSON format:

{{
  "Coherence": "<almost not at all|hardly|neutral|very|highly>",
  "Explanation": "One or two sentences about flow/organization only."
}}

Please DO NOT generate any text other than this JSON.
No markdown/code fences; the result must be loadable via `json.loads()`. [/INST]</s>
"""

def get_completeness_prompt(original_md_note, candidate_note):
    return f"""
<s> [INST] You are an expert in clinical summarization evaluation.

Below is a clinical note originally written by a physician:
{original_md_note}

And here is a note that was generated and then corrected to match the original:
{candidate_note}

You are tasked with evaluating the **Completeness** of the corrected note — that is, how well it captures all the key information from the original physician-authored note.

You are NOT evaluating whether the values are correct (that’s **Correctness**) or whether any irrelevant material was added (that’s **Relevance/Precision**). This evaluation is solely about whether **important information was lost or omitted**.

---

### Likert Scale for Completeness

- **Almost not at all**: The note is missing nearly all relevant information.
- **Hardly**: Several key details are missing; the clinical picture is incomplete.
- **Neutral**: Most of the core content is present, but a few important fields are missing.
- **Very**: Only minor, non-critical information is omitted.
- **Highly**: The note captures everything important from the original without loss.

---

### Example: Prostate Cancer Monitoring

#### MD Note:
"Patient returns for follow-up. PSA is 0.3. Testosterone 465. Axumin PET from 06/2021 shows focal uptake at tip of sacrum. Restarted Lupron on 06/02/2021."

#### Candidate Notes (Completeness Variants):

- **Almost not at all**:
"Patient returned for follow-up. Discussion held."
→ Missing all numerical data and imaging. The note is vague and devoid of substance.

- **Hardly**:
"Follow-up visit. PSA discussed. Restarted Lupron."
→ Omits testosterone, scan findings, scan date. Key information is missing.

- **Neutral**:
"PSA is 0.3. Restarted Lupron on 06/02/2021. Imaging was done."
→ Mentions some important fields, but omits testosterone value and specific imaging details.

- **Very**:
"PSA 0.3. Testosterone 465. Restarted Lupron. Imaging showed sacral lesion."
→ Contains nearly all content; imaging date is missing.

- **Highly**:
"Follow-up visit. PSA 0.3. Testosterone 465. PET from 06/2021 shows sacral uptake. Restarted Lupron on 06/02/2021."
→ All critical content retained.

---

### Your Output

Now, using the examples above, rate the **Completeness** of the candidate note using the following JSON format:

{{
  "Completeness": "very",
  "Explanation": "The note covers all key labs and treatment decisions but omits the specific date of the PET scan.",
}}

or

{{
  "Completeness": "highly",
  "Explanation": "All relevant fields from the MD note — including labs, imaging, and treatment actions — are preserved in full.",
}}

> ⚠️ NOTE: Spurious or irrelevant information **does not affect completeness**. A candidate can be **highly complete** even if it includes extra content, as long as all key original information is present.

Please DO NOT generate anything other than the JSON above.

Also avoid formatting wrappers like ```json — your output must be valid JSON that can be parsed using `json.loads()`.

</s>
"""


def get_correctness_prompt(original_md_note, candidate_note):
    return f"""
<s> [INST] You are an expert in clinical documentation evaluation.

The following is a note written by a medical doctor:
{original_md_note}

Below is a candidate note that has been derived from a hallucinated version of the original and corrected by a model:
{candidate_note}

Your task is to evaluate the **Correctness** of the candidate note — whether each clinical **value** in the candidate matches the corresponding value in the original doctor-authored note, and grade the **clinical criticality** of any incorrect/mismatched values.

You are only evaluating value accuracy. Do not consider whether information is missing (that's Recall/Completeness) or whether extra information was added (that's Precision/Relevance). You are concerned solely with **incorrect or changed values**.

---

### Likert Scale for Correctness

- **Almost not at all**: Most values are incorrect or contradict the original.
- **Hardly**: Many values are wrong, though some match.
- **Neutral**: Most values are correct, but a few are inaccurate.
- **Very**: Nearly all values are accurate, with only minor discrepancies.
- **Highly**: All values match exactly.

**Criticality rubric (for EACH incorrect/mismatched value):**
- **Critical** (weight 3): Stage/TNM or metastatic status errors; wrong primary diagnosis/site/laterality; incorrect histology/grade; wrong management-changing biomarkers; incorrect systemic therapy/regimen; wrong radiation dose/fractions; incorrect surgery margins/nodes; wrong DOD.
- **Important** (weight 2): Incorrect imaging/lab values that inform but don't alter stage; wrong cycle counts; incorrect dose holds/reductions; misreported adverse effects; wrong follow-up timing.
- **Minor** (weight 1): Incorrect vitals; wrong ROS details; incorrect social/family history; wrong administrative details; misreported generic counseling.

---

### Example: Prostate Cancer with Critical Error

#### MD Note:
"PSA is 0.3. Stage T2N0M0. BRCA2 positive. Started enzalutamide 06/02/2021."

#### Candidate Note:
"PSA is 3.0. Stage T3N1M0. BRCA2 positive. Started enzalutamide in June 2021."

#### Evaluation:
{{
  "Correctness": "hardly",
  "Explanation": "Critical errors in PSA value and staging that would change management.",
  "InaccurateFields": ["PSA value", "Stage", "Enzalutamide start date"],
  "InaccurateFieldsDetailed": [
    {{"text": "PSA 3.0 vs 0.3", "category": "imaging", "criticality": "important", "reason": "10-fold error in key monitoring lab"}},
    {{"text": "Stage T3N1M0 vs T2N0M0", "category": "stage", "criticality": "critical", "reason": "Incorrect staging changes prognosis and treatment"}},
    {{"text": "June 2021 vs 06/02/2021", "category": "treatment", "criticality": "minor", "reason": "Imprecise but correct month"}}
  ],
  "WeightedIncorrect": 6
}}

---

Return your evaluation in **JSON ONLY**:

{{
  "Correctness": "<almost not at all|hardly|neutral|very|highly>",
  "Explanation": "Brief explanation of value accuracy.",
  "InaccurateFields": ["<list of fields with incorrect values>"],
  "InaccurateFieldsDetailed": [
    {{"text": "<incorrect value vs correct value>",
      "category": "<stage|diagnosis|treatment|radiation|surgery|biomarker|imaging|follow_up|admin|social|vitals|other>",
      "criticality": "<critical|important|minor>",
      "reason": "<why this level>"}}
  ],
  "WeightedIncorrect": <int>  # sum weights (critical=3, important=2, minor=1)
}}

Please DO NOT generate anything except the JSON above.
No markdown/code fences; the result must be loadable with `json.loads()`. [/INST]</s>
"""