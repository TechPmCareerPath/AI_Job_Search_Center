from query_builder import (
    VISA_EXPLICIT, VISA_NOT_RULED_OUT, form_to_payload, load_saved_payload, payload_to_form,
)


def test_empty_form_sends_only_paging_fields():
    assert form_to_payload({}) == {
        "posted_at_max_age_days": 30, "include_total_results": True, "limit": 10,
    }


def test_singapore_visa_not_ruled_out():
    payload = form_to_payload({
        "titles": "marketing, growth ,, customer success",
        "exclude_titles": "intern",
        "countries": ["Singapore"],
        "visa": VISA_NOT_RULED_OUT,
    })
    assert payload["job_title_or"] == ["marketing", "growth", "customer success"]
    assert payload["job_title_not"] == ["intern"]
    assert payload["job_country_code_or"] == ["SG"]
    assert payload["visa_sponsorship_or"] == ["offers"]
    assert payload["include_unknown"] == ["visa_sponsorship"]


def test_explicit_visa_does_not_include_unknown():
    payload = form_to_payload({"visa": VISA_EXPLICIT})
    assert payload["visa_sponsorship_or"] == ["offers"]
    assert "include_unknown" not in payload


def test_seniority_unlabeled_toggle():
    kept = form_to_payload({"seniority": ["Senior"], "include_unlabeled_seniority": True})
    dropped = form_to_payload({"seniority": ["Senior"], "include_unlabeled_seniority": False})
    assert kept["job_seniority_or"] == ["senior"] and kept["include_unknown"] == ["seniority"]
    assert "include_unknown" not in dropped


def test_salary_floor_keeps_unsalaried_jobs_by_default():
    payload = form_to_payload({"min_salary_usd": 52000})
    assert payload["min_salary_usd"] == 52000
    assert payload["include_unknown"] == ["salary"]


def test_round_trip():
    form = {
        "titles": "marketing, growth", "exclude_titles": "intern", "countries": ["Singapore"],
        "cities": "", "seniority": ["Mid level"], "include_unlabeled_seniority": True,
        "work_arrangement": ["Hybrid"], "visa": VISA_NOT_RULED_OUT, "min_salary_usd": 52000,
        "include_no_salary": True, "posted_within_days": 14, "limit": 20,
    }
    assert payload_to_form(form_to_payload(form)) == form


QUERY_YAML_PRESETS = {
    "procurement": '{"job_title_or":["Buyer","Procurement","Purchasing Agent","Procurement Specialist","Procurement Coordinator"], "job_seniority_or":["Entry_Level"], "include_unlabeled_seniority": true, "job_country_code_or":["US"], "job_location_or":["Austin","Houston","San Antonio","Dallas","Garland","Fort Worth"], "posted_at_max_age_days":30, "include_total_results": true, "limit":10}',
    "program manager": '{"job_title_or":["program manager"], "job_seniority_or":["Senior"], "include_unlabeled_seniority": true, "job_country_code_or":["US"], "job_location_or":["Austin","Houston","San Antonio","Dallas","Garland","Fort Worth"], "posted_at_max_age_days":30, "include_total_results": true, "limit":10}',
}


def test_query_yaml_presets_load_and_rebuild_equivalently():
    for name, raw in QUERY_YAML_PRESETS.items():
        original = load_saved_payload(raw)
        rebuilt = form_to_payload(payload_to_form(original))
        for key in ("job_title_or", "job_country_code_or", "job_location_or", "limit", "posted_at_max_age_days"):
            assert rebuilt.get(key) == original.get(key), (name, key)
        assert [s.lower() for s in rebuilt["job_seniority_or"]] == [s.lower() for s in original["job_seniority_or"]]
        assert "seniority" in rebuilt["include_unknown"], name


def test_load_saved_payload_accepts_json_strings_and_mappings():
    assert load_saved_payload('{"limit": 5}') == {"limit": 5}
    assert load_saved_payload({"limit": 5}) == {"limit": 5}
    assert load_saved_payload(None) == {}
