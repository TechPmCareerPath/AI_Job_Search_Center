"""
Guards for behaviour the README promises but no unit test can reach, because app.py runs
Streamlit on import. These read app.py as text and check the wiring is still there.

Why: on 2026-10-10 an edit made from an older copy of app.py removed the Check column and
"Refresh posting status" went back to asking JobsPipe about every tracked job, while the
README kept describing the ticked-rows behaviour. The existing tests stayed green.
"""
import ast
from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
TREE = ast.parse(APP)


def _function(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} is not defined in app.py")


def test_refresh_posting_statuses_takes_the_ticked_job_ids():
    args = [a.arg for a in _function("refresh_posting_statuses").args.args]
    assert args == ["tracker_data", "jobs_api_key", "job_ids"], (
        "Refresh must only check the jobs the user ticked; the README says so."
    )


def test_tracker_has_a_check_column_feeding_the_refresh_button():
    assert 'df.insert(0, "check", False)' in APP, "the Check column is missing from the tracker table"
    assert "selected_job_ids(edited_df.to_dict" in APP, "ticked rows no longer drive Refresh posting status"
    assert 'st.column_config.CheckboxColumn("Check"' in APP


def test_job_links_stay_sanitised():
    # Craig's 2026-10-10 change: plain markdown link after a scheme + hostname check, no raw HTML.
    assert "urlsplit(source_url)" in APP
    assert "[Open job posting](" in APP
    assert "unsafe_allow_html=True" not in APP.split("if source_url:")[1].split("key_skills")[0]
