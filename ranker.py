"""
Ranking module for AI Hiring Agent.

Responsibilities:
  1. Pre-validate candidates (reject if CGPA is None)
  2. Normalize numeric fields
  3. Compute composite score
  4. Deduplicate by email
  5. Sort and return top 10
"""

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

W_CGPA  = 0.30
W_EXP   = 0.30
W_PROJ  = 0.25
W_12TH  = 0.10
W_10TH  = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_cgpa(cgpa: float) -> float:
    """Scale CGPA (0-10) to 0-100."""
    return cgpa * 10


def _normalize_exp(years: float) -> float:
    """Cap experience at 5 years, scale to 0-100."""
    return min((years / 5) * 100, 100)


def _normalize_proj(count: float) -> float:
    """Cap project count at 5, scale to 0-100."""
    return min((count / 5) * 100, 100)


def _compute_score(candidate: dict) -> float:
    norm_cgpa = _normalize_cgpa(candidate["cgpa"])
    norm_exp  = _normalize_exp(candidate["years_of_exp"] or 0)
    norm_proj = _normalize_proj(candidate["project_count"] or 0)
    marks_12  = candidate["12th_marks"] or 0
    marks_10  = candidate["10th_marks"]  or 0

    return (
        (norm_cgpa * W_CGPA) +
        (norm_exp  * W_EXP)  +
        (norm_proj * W_PROJ) +
        (marks_12  * W_12TH) +
        (marks_10  * W_10TH)
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def rank_candidates(results: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Process a list of candidate result dicts from the backend.

    Returns
    -------
    all_scored : list[dict]
        Every candidate that passed pre-validation, with 'score' added.
        Includes both ranked and unranked (if > 10).
    top_10 : list[dict]
        Up to 10 highest-scoring candidates, sorted descending by score.
    """
    seen_emails: set[str] = set()
    eligible: list[dict]  = []

    for candidate in results:
        # Only process successfully extracted candidates
        if candidate.get("status") != "SUCCESS":
            continue

        # Pre-validation: reject if CGPA is missing
        if candidate.get("cgpa") is None:
            candidate = {**candidate, "status": "FAILED", "failure_reason": "CGPA is required for ranking"}
            continue

        # Deduplication by email
        email = candidate.get("candidate_email")
        if email:
            if email in seen_emails:
                continue
            seen_emails.add(email)

        # Compute score (outside loop ranking - collected first, sorted after)
        scored = {**candidate, "score": round(_compute_score(candidate), 4)}
        eligible.append(scored)

    # Sort all eligible candidates descending by score (ranking done AFTER loop)
    eligible.sort(key=lambda c: c["score"], reverse=True)

    top_10 = eligible[:10]

    return eligible, top_10
