from datetime import date

from job_signals import (
    CLOSED, MAYBE_CLOSED, NOT_FOUND, OPEN, job_badges, posting_statuses, selected_job_ids, skill_candidates,
)


def test_open_if_any_copy_is_active():
    rows = [
        {"id": "1", "status": "closed", "closed_reason": "stale", "last_seen_at": None},
        {"id": "1", "status": "active", "last_seen_at": "2026-09-28 00:25:14"},
    ]
    assert posting_statuses(rows, ["1"]) == {"1": {"status": OPEN, "last_seen": "2026-09-28"}}


def test_closed_only_when_verified():
    verified = [{"id": "2", "status": "closed", "closed_reason": "gone", "last_seen_at": "2026-09-01 10:00:00"}]
    unverified = [{"id": "3", "status": "closed", "closed_reason": "stale"}]
    assert posting_statuses(verified, ["2"])["2"]["status"] == CLOSED
    assert posting_statuses(unverified, ["3"])["3"] == {"status": MAYBE_CLOSED, "last_seen": ""}


def test_ids_without_rows_are_not_found_and_ids_are_compared_as_strings():
    assert posting_statuses([{"id": 4, "status": "active"}], [4, "5"]) == {
        "4": {"status": OPEN, "last_seen": ""},
        "5": {"status": NOT_FOUND, "last_seen": ""},
    }


def test_badges():
    row = {
        "salary_string": "$4,000 - $6,000 per month", "applicant_count": 25, "ghost_score": 80,
        "employer_type": "agency", "last_seen_at": "2026-09-01 08:00:00",
    }
    assert job_badges(row, today=date(2026, 9, 28)) == [
        "💰 $4,000 - $6,000 per month",
        "👥 25 applicants (early)",
        "👻 Likely ghost job",
        "🏢 Posted by a recruitment agency",
        "⏳ Not seen live for 27 days",
    ]


def test_badges_fall_back_to_annual_salary_and_stay_quiet_when_nothing_is_known():
    assert job_badges({"min_annual_salary_usd": 90000, "max_annual_salary_usd": 120000}) == ["💰 $90,000 - $120,000 / year"]
    assert job_badges({"ghost_score": 20, "employer_type": "employer", "applicant_count": None}) == []


def test_skill_candidates_skip_soft_skills_and_count_each_job_once():
    rows = [
        {"keyword_slugs": ["communication", "seo", "seo"], "technology_slugs": ["excel"]},
        {"keyword_slugs": ["seo", "leadership", "canva"], "technology_slugs": []},
        {"keyword_slugs": None, "technology_slugs": ["excel"]},
    ]
    assert skill_candidates(rows) == ["excel", "seo", "canva"]
    assert skill_candidates(rows, top_n=1) == ["excel"]


def test_selected_job_ids_keeps_only_ticked_rows_with_a_jobspipe_id():
    rows = [
        {"check": True, "job_id": "a1"},
        {"check": False, "job_id": "b2"},
        {"check": True, "job_id": ""},          # added by hand: no JobsPipe id
        {"check": True, "job_id": None},
        {"check": float("nan"), "job_id": "c3"},  # untouched checkbox comes back as NaN
        {"check": True, "job_id": 44},
        {"job_id": "d4"},                        # legacy row without the column
    ]
    assert selected_job_ids(rows) == ["a1", "44"]
