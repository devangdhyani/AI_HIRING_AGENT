"""
Backend processing for AI Hiring Agent.

Pipeline per candidate:
  1. PDF text extraction  (pdfplumber)
  2. Text cleaning + truncation
  3. LLM extraction       (Groq API, primary → fallback)
  4. JSON parsing + validation
  5. Return structured result dict

No ranking / scoring here.
"""

import io
import json
import os
import re
import time

import pdfplumber
from dotenv import load_dotenv
from groq import Groq

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIMARY_MODEL  = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"
MAX_TEXT_CHARS = 8000
LLM_TIMEOUT    = 15        # seconds (passed via Groq client httpx timeout)
MAX_RETRIES    = 2         # per model
RETRY_DELAY    = 0.75      # seconds between retries

NUMERIC_FIELDS = {"10th_marks", "12th_marks", "cgpa", "years_of_exp", "project_count"}
STRING_FIELDS  = {"candidate_name", "candidate_email"}
ALL_FIELDS     = NUMERIC_FIELDS | STRING_FIELDS

PROMPT_TEMPLATE = """\
Extract structured data from the resume below and return ONLY a valid JSON object.
No explanation, no markdown, no extra text - JSON only.

Output format:
{{
  "candidate_name": string or null,
  "candidate_email": string or null,
  "10th_marks": number or null,
  "12th_marks": number or null,
  "cgpa": number or null,
  "years_of_exp": number or null,
  "project_count": number or null
}}

Extraction rules:

candidate_name:
- Full name of the candidate.
- Return null if not found.

candidate_email:
- Email address of the candidate.
- Return null if not found.

10th_marks / 12th_marks:
- Extract the numeric percentage value only (range 0-100).
- Accepted formats: "85%", "85 percent", "85/100" -> return 85
- Return null if not found.

cgpa:
- Extract and NORMALIZE to a 10-point scale using these rules:
  Rule 1 - Already out of 10: return as-is.
    Example: "CGPA: 8.2", "GPA: 8.2/10", "8.2 CGPA" -> return 8.2
  Rule 2 - Out of 4.0 scale: convert using formula (value / 4) * 10, round to 2 decimals.
    Example: "3.2/4.0", "GPA: 3.6/4" -> return 8.0, 9.0
  Rule 3 - Given as percentage: convert using formula value / 10, round to 2 decimals.
    Example: "85%" as CGPA -> return 8.5
- Return null if CGPA/GPA is not mentioned at all.

years_of_exp:
- Sum total work experience across ALL roles mentioned.
- If the candidate is a fresher or explicitly states no experience -> return 0.
- Express as a decimal number (e.g. 2.5 for two and a half years).
- Return null only if it is impossible to determine any value.

project_count:
- Count the number of distinct projects explicitly listed.
- Do NOT count internships or work experience entries as projects.
- Return 0 if no projects are mentioned.
- Return null only if the section is completely ambiguous.

General rules:
- Return null for any field that cannot be determined.
- Do NOT include any text outside the JSON object.

Resume Text:
{cleaned_text}"""

# ---------------------------------------------------------------------------
# Module-level Groq client (initialised once after env is loaded)
# ---------------------------------------------------------------------------

_groq_client: Groq | None = None


def _get_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        raise RuntimeError("Groq client not initialised. Call load_api_key() first.")
    return _groq_client


# ---------------------------------------------------------------------------
# Step 3 — API key loading
# ---------------------------------------------------------------------------

def load_api_key() -> None:
    """Load GROQ_API_KEY from .env and initialise the Groq client."""
    global _groq_client
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is missing. "
            "Add it to a .env file in the project root: GROQ_API_KEY=your_key_here"
        )
    _groq_client = Groq(api_key=api_key, timeout=LLM_TIMEOUT)


# ---------------------------------------------------------------------------
# Step 1 — PDF extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF given its raw bytes.
    Raises ValueError if extraction yields no usable text.
    """
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("PDF produced no extractable text (scanned image or empty).")
    return full_text


# ---------------------------------------------------------------------------
# Step 2 — Text cleaning
# ---------------------------------------------------------------------------

def clean_text(raw: str) -> str:
    """
    Clean and truncate resume text before sending to the LLM.
    """
    # Remove non-ASCII characters (keep basic latin + common punctuation)
    text = raw.encode("ascii", errors="ignore").decode("ascii")

    # Normalize various line-ending styles
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse repeated spaces / tabs on each line
    text = re.sub(r"[ \t]+", " ", text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    # Truncate
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]

    return text


# ---------------------------------------------------------------------------
# Step 4 — LLM extraction
# ---------------------------------------------------------------------------

def _call_llm(model: str, cleaned_text: str) -> str:
    """
    Call Groq with the given model. Returns raw response content string.
    Raises on any API error so the caller can retry or fall back.
    """
    prompt = PROMPT_TEMPLATE.format(cleaned_text=cleaned_text)
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def _call_with_retries(model: str, cleaned_text: str) -> str:
    """
    Attempt up to MAX_RETRIES calls on a single model.
    Returns raw LLM content on success, raises last exception on total failure.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _call_llm(model, cleaned_text)
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise last_exc  # type: ignore[misc]


def extract_candidate_data(cleaned_text: str) -> str:
    """
    Try primary model, then fallback. Returns raw JSON string from LLM.
    Raises RuntimeError if both models fail.
    """
    # --- Primary ---
    try:
        return _call_with_retries(PRIMARY_MODEL, cleaned_text)
    except Exception as primary_exc:
        primary_msg = str(primary_exc)

    # --- Delay before switching model ---
    time.sleep(RETRY_DELAY)

    # --- Fallback ---
    try:
        return _call_with_retries(FALLBACK_MODEL, cleaned_text)
    except Exception as fallback_exc:
        raise RuntimeError(
            f"Both models failed. Primary: {primary_msg} | Fallback: {fallback_exc}"
        )


# ---------------------------------------------------------------------------
# Step 5 — JSON parsing + validation
# ---------------------------------------------------------------------------

def _extract_json_block(raw: str) -> str:
    """
    Attempt to locate the first {...} block in the LLM response
    in case extra text is present.
    """
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw  # let json.loads raise a clear error


def _validate_record(data: dict) -> None:
    """
    Validate types and value ranges.
    Raises ValueError with a descriptive message on any violation.
    """
    # Ensure all expected keys are present (fill missing with null)
    for field in ALL_FIELDS:
        data.setdefault(field, None)

    # String fields: must be str or None
    for field in STRING_FIELDS:
        val = data[field]
        if val is not None and not isinstance(val, str):
            raise ValueError(f"Field '{field}' must be string or null, got {type(val).__name__}.")

    # Numeric fields: must be int/float or None
    for field in NUMERIC_FIELDS:
        val = data[field]
        if val is None:
            continue
        if not isinstance(val, (int, float)):
            raise ValueError(f"Field '{field}' must be numeric or null, got {type(val).__name__}.")

        val = float(val)

        if field == "cgpa" and val > 10:
            raise ValueError(f"'cgpa' value {val} exceeds maximum of 10.")
        if field in {"10th_marks", "12th_marks"} and not (0 <= val <= 100):
            raise ValueError(f"'{field}' value {val} is outside valid range 0–100.")
        if field == "years_of_exp" and val < 0:
            raise ValueError(f"'years_of_exp' value {val} cannot be negative.")
        if field == "project_count" and val < 0:
            raise ValueError(f"'project_count' value {val} cannot be negative.")


def parse_and_validate(raw_llm_output: str) -> dict:
    """
    Extract, parse, and validate the JSON from LLM output.
    Returns the validated dict. Raises ValueError/json.JSONDecodeError on failure.
    """
    json_str = _extract_json_block(raw_llm_output)
    data = json.loads(json_str)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}.")

    _validate_record(data)
    return data


# ---------------------------------------------------------------------------
# Step 6 + 7 — Per-candidate processing + output structure
# ---------------------------------------------------------------------------

def _make_failed(file_name: str, reason: str) -> dict:
    return {
        "file_name":       file_name,
        "candidate_name":  None,
        "candidate_email": None,
        "10th_marks":      None,
        "12th_marks":      None,
        "cgpa":            None,
        "years_of_exp":    None,
        "project_count":   None,
        "status":          "FAILED",
        "failure_reason":  reason,
    }


def process_candidate(file_name: str, file_bytes: bytes) -> dict:
    """
    Full pipeline for a single candidate file.
    Always returns a result dict — never raises.
    """
    # Step 1 — PDF extraction
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except Exception as exc:
        return _make_failed(file_name, f"PDF extraction failed: {exc}")

    # Step 2 — Clean text
    try:
        cleaned_text = clean_text(raw_text)
    except Exception as exc:
        return _make_failed(file_name, f"Text cleaning failed: {exc}")

    # Step 4 — LLM extraction
    try:
        raw_llm = extract_candidate_data(cleaned_text)
    except Exception as exc:
        return _make_failed(file_name, f"LLM extraction failed: {exc}")

    # Step 5 — Parse + validate
    try:
        data = parse_and_validate(raw_llm)
    except Exception as exc:
        return _make_failed(file_name, f"JSON parse/validation failed: {exc}")

    return {
        "file_name":       file_name,
        "candidate_name":  data.get("candidate_name"),
        "candidate_email": data.get("candidate_email"),
        "10th_marks":      data.get("10th_marks"),
        "12th_marks":      data.get("12th_marks"),
        "cgpa":            data.get("cgpa"),
        "years_of_exp":    data.get("years_of_exp"),
        "project_count":   data.get("project_count"),
        "status":          "SUCCESS",
        "failure_reason":  None,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def process_batch(files: list[tuple[str, bytes]]) -> list[dict]:
    """
    Process a batch of (file_name, file_bytes) tuples sequentially.

    Parameters
    ----------
    files : list of (str, bytes)
        Each tuple is (original filename, raw PDF bytes).

    Returns
    -------
    list[dict]
        One result dict per candidate.
    """
    results: list[dict] = []
    for file_name, file_bytes in files:
        result = process_candidate(file_name, file_bytes)
        results.append(result)
        # Small delay between candidates to respect API rate limits
        time.sleep(RETRY_DELAY)
    return results
