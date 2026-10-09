"""
Translate between the Search Builder form in the UI and a JobsPipe search payload.

Kept free of Streamlit so both directions can be tested on their own:
  form_to_payload(form)    -> dict sent to POST /v1/jobs/search
  payload_to_form(payload) -> form values, used to load a saved search into the UI
  load_saved_payload(raw)  -> a saved search as a dict (query.yaml stores them as JSON strings)
"""
import json

COUNTRIES = {
    "United States": "US", "United Kingdom": "GB", "Canada": "CA", "Australia": "AU",
    "Singapore": "SG", "Ireland": "IE", "Germany": "DE", "France": "FR",
    "Netherlands": "NL", "Spain": "ES", "Portugal": "PT", "Switzerland": "CH",
    "Sweden": "SE", "Israel": "IL", "United Arab Emirates": "AE", "India": "IN",
    "Hong Kong": "HK", "Japan": "JP", "New Zealand": "NZ",
}

SENIORITY = {
    "Internship": "internship", "Entry level": "entry_level", "Mid level": "mid_level",
    "Senior": "senior", "Director / Lead": "director", "Executive": "executive",
}

WORK_ARRANGEMENTS = {"Remote": "remote", "Hybrid": "hybrid", "On-site": "onsite"}

VISA_ANY = "Doesn't matter"
VISA_NOT_RULED_OUT = "Hide jobs that rule out sponsorship"
VISA_EXPLICIT = "Only jobs that explicitly offer sponsorship"
VISA_OPTIONS = [VISA_ANY, VISA_NOT_RULED_OUT, VISA_EXPLICIT]

POSTED_WITHIN_DAYS = [1, 3, 7, 14, 30]

AGENCY_EMPLOYER_TYPES = ["agency", "broker"]
MAX_GHOST_SCORE = 40

DEFAULT_FORM = {
    "titles": "",
    "exclude_titles": "",
    "countries": [],
    "cities": "",
    "seniority": [],
    "include_unlabeled_seniority": True,
    "work_arrangement": [],
    "visa": VISA_ANY,
    "min_salary_usd": 0,
    "include_no_salary": True,
    "posted_within_days": 30,
    "limit": 10,
    "english_only": False,
    "hide_agencies": False,
    "hide_ghost_jobs": False,
}


def _split(text: str) -> list:
    """'a, b ,,c' -> ['a', 'b', 'c']"""
    return [part.strip() for part in (text or "").split(",") if part.strip()]


def _labels_for(values, mapping: dict) -> list:
    """Map API values back to display labels, case-insensitively; unknown values are dropped."""
    by_value = {v.lower(): label for label, v in mapping.items()}
    return [by_value[v.lower()] for v in (values or []) if v.lower() in by_value]


def form_to_payload(form: dict, discovered_since: str = None) -> dict:
    """Build the JobsPipe request body. Empty fields are left out so they don't filter."""
    f = {**DEFAULT_FORM, **form}
    payload = {}
    include_unknown = []

    if titles := _split(f["titles"]):
        payload["job_title_or"] = titles
    if excluded := _split(f["exclude_titles"]):
        payload["job_title_not"] = excluded
    if f["countries"]:
        payload["job_country_code_or"] = [COUNTRIES[c] for c in f["countries"]]
    if cities := _split(f["cities"]):
        payload["job_location_or"] = cities

    if f["seniority"]:
        payload["job_seniority_or"] = [SENIORITY[s] for s in f["seniority"]]
        if f["include_unlabeled_seniority"]:
            include_unknown.append("seniority")

    if f["work_arrangement"]:
        payload["work_arrangement_or"] = [WORK_ARRANGEMENTS[w] for w in f["work_arrangement"]]
        include_unknown.append("work_arrangement")

    if f["visa"] != VISA_ANY:
        payload["visa_sponsorship_or"] = ["offers"]
    if f["visa"] == VISA_NOT_RULED_OUT:
        include_unknown.append("visa_sponsorship")

    if f["min_salary_usd"]:
        payload["min_salary_usd"] = int(f["min_salary_usd"])
        if f["include_no_salary"]:
            include_unknown.append("salary")

    if include_unknown:
        payload["include_unknown"] = include_unknown

    if f["english_only"]:
        payload["language_or"] = ["en"]
    if f["hide_agencies"]:
        payload["employer_type_not"] = AGENCY_EMPLOYER_TYPES
    if f["hide_ghost_jobs"]:
        payload["max_ghost_score"] = MAX_GHOST_SCORE
    if discovered_since:
        payload["discovered_at_gte"] = discovered_since

    payload["posted_at_max_age_days"] = int(f["posted_within_days"])
    payload["include_total_results"] = True
    payload["limit"] = int(f["limit"])
    return payload


def payload_to_form(payload: dict) -> dict:
    """Load a saved payload (including the older hand-written query.yaml ones) into form values."""
    p = payload or {}
    unknown = set(p.get("include_unknown", []))

    if "offers" not in p.get("visa_sponsorship_or", []):
        visa = VISA_ANY
    elif "visa_sponsorship" in unknown:
        visa = VISA_NOT_RULED_OUT
    else:
        visa = VISA_EXPLICIT

    posted = int(p.get("posted_at_max_age_days", DEFAULT_FORM["posted_within_days"]))

    return {
        "titles": ", ".join(p.get("job_title_or", [])),
        "exclude_titles": ", ".join(p.get("job_title_not", [])),
        "countries": _labels_for(p.get("job_country_code_or"), COUNTRIES),
        "cities": ", ".join(p.get("job_location_or", [])),
        "seniority": _labels_for(p.get("job_seniority_or"), SENIORITY),
        "include_unlabeled_seniority": bool(p.get("include_unlabeled_seniority") or "seniority" in unknown),
        "work_arrangement": _labels_for(p.get("work_arrangement_or"), WORK_ARRANGEMENTS),
        "visa": visa,
        "min_salary_usd": int(p.get("min_salary_usd", 0)),
        "include_no_salary": "salary" in unknown or not p.get("min_salary_usd"),
        "posted_within_days": posted if posted in POSTED_WITHIN_DAYS else DEFAULT_FORM["posted_within_days"],
        "limit": int(p.get("limit", DEFAULT_FORM["limit"])),
        "english_only": p.get("language_or") == ["en"],
        "hide_agencies": bool(p.get("employer_type_not")),
        "hide_ghost_jobs": "max_ghost_score" in p,
    }


def load_saved_payload(raw) -> dict:
    """query.yaml keeps searches as JSON strings; searches saved from the UI are plain mappings."""
    return json.loads(raw) if isinstance(raw, str) else dict(raw or {})
