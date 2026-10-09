"""
Signals about job postings that JobsPipe returns alongside each job.

  posting_statuses(rows, job_ids)       -> {job_id: {"status", "last_seen"}} for the Application Tracker
  job_badges(row, today)                -> short labels for a match card (salary, applicants, ghost risk...)
  skill_candidates(rows, top_n)         -> concrete skills to measure demand for
  selected_job_ids(rows)                -> JobsPipe ids of the tracker rows the user ticked
"""
from collections import Counter
from datetime import date, datetime

OPEN = "Open"
CLOSED = "Closed"
MAYBE_CLOSED = "May be closed"
NOT_FOUND = "Not found"

VERIFIED_CLOSE_REASONS = {"gone", "closed"}
GHOST_RISK_HIGH = 60
STALE_AFTER_DAYS = 14
AGENCY_TYPES = {"agency", "broker"}

SOFT_SKILLS = {
    "communication", "teamwork", "leadership", "mentoring", "attention-to-detail", "problem-solving",
    "collaboration", "time-management", "adaptability", "interpersonal-skills", "organization",
    "critical-thinking", "customer-service", "multitasking", "creativity", "self-motivation",
    "presentation", "negotiation", "decision-making", "work-ethic",
}


def _parse_day(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:19]).date()
    except ValueError:
        return None


def posting_statuses(rows: list, job_ids: list) -> dict:
    """
    One job id can come back as several rows (the same job on several sources).
    It is Open if any copy is active, Closed only if a copy was verified gone or closed,
    and "May be closed" when every copy was closed without verification (e.g. not seen for a while).
    """
    by_id = {}
    for row in rows:
        by_id.setdefault(str(row.get("id")), []).append(row)

    statuses = {}
    for job_id in map(str, job_ids):
        copies = by_id.get(job_id, [])
        seen = [d for d in (_parse_day(c.get("last_seen_at")) for c in copies) if d]
        last_seen = max(seen).isoformat() if seen else ""
        if not copies:
            status = NOT_FOUND
        elif any(c.get("status") == "active" for c in copies):
            status = OPEN
        elif any(c.get("closed_reason") in VERIFIED_CLOSE_REASONS for c in copies):
            status = CLOSED
        else:
            status = MAYBE_CLOSED
        statuses[job_id] = {"status": status, "last_seen": last_seen}
    return statuses


def job_badges(row: dict, today: date = None) -> list:
    today = today or date.today()
    badges = []

    if row.get("salary_string"):
        badges.append(f"💰 {row['salary_string']}")
    elif row.get("min_annual_salary_usd"):
        low, high = row["min_annual_salary_usd"], row.get("max_annual_salary_usd")
        badges.append(f"💰 ${low:,.0f}" + (f" - ${high:,.0f}" if high and high != low else "") + " / year")

    applicants = row.get("applicant_count")
    if applicants is not None:
        badges.append(f"👥 {applicants} applicants" + (" (early)" if applicants <= 25 else ""))

    ghost = row.get("ghost_score")
    if ghost is not None and ghost >= GHOST_RISK_HIGH:
        badges.append("👻 Likely ghost job")

    if row.get("employer_type") in AGENCY_TYPES:
        badges.append("🏢 Posted by a recruitment agency")

    last_seen = _parse_day(row.get("last_seen_at"))
    if last_seen and (today - last_seen).days > STALE_AFTER_DAYS:
        badges.append(f"⏳ Not seen live for {(today - last_seen).days} days")

    return badges


def selected_job_ids(rows: list) -> list:
    """
    JobsPipe ids of the tracker rows whose "check" box is ticked, in table order.
    Rows added by hand have no id and are skipped; an untouched box can come back as NaN.
    """
    ids = []
    for row in rows:
        if str(row.get("check")).lower() != "true":
            continue
        job_id = row.get("job_id")
        text = "" if job_id is None else str(job_id).strip()
        if text and text.lower() != "nan":
            ids.append(text)
    return ids


def skill_candidates(rows: list, top_n: int = 8) -> list:
    counts = Counter()
    for row in rows:
        counts.update(set(row.get("keyword_slugs") or []) | set(row.get("technology_slugs") or []))
    ranked = sorted(counts, key=lambda slug: (-counts[slug], slug))
    return [slug for slug in ranked if slug not in SOFT_SKILLS][:top_n]
