"""
Guards for wiring that unit tests cannot reach, because app.py starts Streamlit on import.
They read app.py as text and check that the Check column still feeds "Refresh posting status"
and that job links stay sanitised.
"""
import ast
import re
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
    assert args[-1] == "job_ids", (
        "Refresh must only check the jobs the user ticked, as the README says."
    )


def test_tracker_has_a_check_column_feeding_the_refresh_button():
    assert re.search(r'df\.insert\(\s*0,\s*["\']check["\']', APP), "the Check column is missing from the tracker table"
    assert "selected_job_ids(edited_df.to_dict" in APP, "ticked rows no longer drive Refresh posting status"
    assert re.search(r'CheckboxColumn\(\s*["\']Check["\']', APP)


def test_job_links_stay_sanitised():
    # Plain markdown link after a scheme + hostname check, no raw HTML.
    start = APP.index("if source_url:")
    link_block = APP[start:APP.index("key_skills", start)]
    assert "urlsplit(source_url)" in link_block
    assert "[Open job posting](" in link_block
    assert "unsafe_allow_html=True" not in link_block
