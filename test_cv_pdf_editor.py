import pymupdf
import pytest

from cv_pdf_editor import (
    _split_font_name, apply_edits, check_edits, find_blocks, load_fonts, render_pages,
)

HELV = pymupdf.Font("helv").buffer


def text(page, x, y, s, size=9):
    page.insert_text((x, y), s, fontname="helv", fontsize=size)


def dot(page, x, y):
    page.draw_circle((x, y - 3), 1.5, color=(0, 0, 0), fill=(0, 0, 0))


def make_cv(path):
    """
    Two-column CV. Left: a contact line with a one-off icon, a language list, a 3-line summary.
    Right: a heading, two drawn-dot bullets (one wraps), a bullet typed as a glyph, a date line.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    page.draw_circle((34, 97), 2.2, color=(1, 1, 1), fill=(1, 1, 1))
    text(page, 40, 100, "Singapore")
    for i, lang in enumerate(["French: Native", "English: Fluent", "Hebrew: Intermediate"]):
        text(page, 30, 140 + i * 14, lang)
    for i, s in enumerate(["Client success professional with SaaS and",
                           "hospitality experience, skilled in growth,",
                           "onboarding and cross-functional work."]):
        text(page, 30, 220 + i * 14, s)

    text(page, 300, 60, "EXPERIENCE", size=14)
    dot(page, 294, 100)
    dot(page, 294, 138)
    text(page, 300, 100, "Led onboarding for enterprise clients across")
    text(page, 300, 114, "three regions and two product lines.")
    text(page, 300, 138, "Grew traffic from 100 to 40K visitors.")
    text(page, 300, 170, "• Ran events for 70+ participants.")
    text(page, 300, 300, "2024 - 2025")
    page.draw_rect(pymupdf.Rect(290, 290, 560, 305), color=(0.8, 0.2, 0.2))
    doc.save(path)


@pytest.fixture
def cv(tmp_path):
    path = str(tmp_path / "cv.pdf")
    make_cv(path)
    return path


@pytest.fixture
def fonts(cv):
    return load_fonts(find_blocks(cv), lambda _: HELV)


def test_font_name_parsing():
    assert _split_font_name("AAAAAA+Montserrat-SemiBoldItalic") == ("Montserrat", True, 600)
    assert _split_font_name("OpenSans-Regular") == ("Open Sans", False, 400)
    assert _split_font_name("Lato") == ("Lato", False, 400)


def test_finds_bullets_and_paragraphs_in_reading_order(cv):
    assert [b["text"] for b in find_blocks(cv)] == [
        "Client success professional with SaaS and hospitality experience, skilled in growth, onboarding and cross-functional work.",
        "Led onboarding for enterprise clients across three regions and two product lines.",
        "Grew traffic from 100 to 40K visitors.",
        "Ran events for 70+ participants.",
    ]


def test_skips_headings_dates_contact_lines_and_short_lists(cv):
    texts = " | ".join(b["text"] for b in find_blocks(cv))
    for left_alone in ("EXPERIENCE", "2024 - 2025", "Singapore", "French: Native"):
        assert left_alone not in texts


def test_rewrites_one_bullet_and_leaves_everything_else(cv, fonts, tmp_path):
    blocks = find_blocks(cv)
    out = str(tmp_path / "out.pdf")
    report = apply_edits(cv, blocks, {1: "Onboarded enterprise hotel clients across three regions and two products."},
                         fonts, out)
    assert [a["id"] for a in report["applied"]] == [1] and report["skipped"] == []

    with pymupdf.open(out) as doc, pymupdf.open(cv) as original:
        page = doc[0]
        assert "Onboarded enterprise hotel clients" in page.get_text()
        assert "Led onboarding" not in page.get_text()
        for untouched in ("EXPERIENCE", "Grew traffic from 100 to 40K visitors.", "2024 - 2025",
                          "hospitality experience, skilled in growth,", "Singapore"):
            assert untouched in page.get_text()
        assert len(page.get_drawings()) == len(original[0].get_drawings())


def test_new_text_sits_on_the_original_baselines(cv, fonts, tmp_path):
    out = str(tmp_path / "out.pdf")
    apply_edits(cv, find_blocks(cv), {1: "Onboarded enterprise hotel clients across three regions and two product lines today."},
                fonts, out)
    with pymupdf.open(out) as doc:
        baselines = sorted({round(s["origin"][1]) for b in doc[0].get_text("dict")["blocks"] if b["type"] == 0
                            for l in b["lines"] for s in l["spans"] if s["origin"][0] > 290 and 90 < s["origin"][1] < 120})
    assert baselines == [100, 114]


def test_typed_bullet_glyph_is_kept(cv, fonts, tmp_path):
    out = str(tmp_path / "out.pdf")
    blocks = find_blocks(cv)
    glyph = blocks[3]["prefix"]
    assert glyph.strip() in "•·"
    report = apply_edits(cv, blocks, {3: "Hosted events for 70+ guests."}, fonts, out)
    assert report["applied"][0]["new"] == "Hosted events for 70+ guests."
    with pymupdf.open(out) as doc:
        assert f"{glyph}Hosted events for 70+ guests." in doc[0].get_text()


def test_rejects_edits_that_drop_a_number(cv, fonts):
    plans, rejected = check_edits(find_blocks(cv), {2: "Grew website traffic through SEO."}, fonts)
    assert plans == {} and rejected[0]["reason"] == "dropped 100, 40 from the original"


def test_too_long_edit_is_rejected_with_line_counts(cv, fonts, tmp_path):
    blocks = find_blocks(cv)
    long_text = ("Grew website traffic from 100 to 40K monthly visitors through SEO, "
                 "content optimisation, keyword research and backlink building.")
    _, rejected = check_edits(blocks, {2: long_text}, fonts)
    assert rejected[0]["lines_available"] == 1 and rejected[0]["lines_needed"] > 1

    out = str(tmp_path / "out.pdf")
    apply_edits(cv, blocks, {2: long_text}, fonts, out)
    with pymupdf.open(out) as doc:
        assert "Grew traffic from 100 to 40K visitors." in doc[0].get_text()


def test_missing_font_is_rejected(cv):
    blocks = find_blocks(cv)
    _, rejected = check_edits(blocks, {2: "Grew traffic from 100 to 40K users."}, load_fonts(blocks, lambda _: None))
    assert "not available" in rejected[0]["reason"]


def test_render_pages(cv):
    with open(cv, "rb") as f:
        pages = render_pages(f.read(), dpi=30)
    assert len(pages) == 1 and pages[0].startswith(b"\x89PNG")
