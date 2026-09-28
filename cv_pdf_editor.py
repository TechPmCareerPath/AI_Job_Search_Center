"""
Rewrite text inside a PDF resume while keeping its design: layout, photo, shapes, colours and
every untouched line stay exactly as they were.

  find_blocks(pdf_path)                           -> editable text blocks (bullets and paragraphs)
  load_fonts(blocks, resolver)                    -> the fonts needed to write into those blocks
  check_edits(blocks, edits, fonts)               -> which edits can be written, and why others can't
  apply_edits(pdf_path, blocks, edits, fonts, out) -> writes the edited PDF, reports applied / skipped
  render_pages(pdf_bytes)                         -> PNG previews of each page
  google_font_resolver(cache_dir)                 -> fetches the fonts a PDF uses from Google Fonts

Works on PDFs that contain real text laid out line by line (Canva, Word, Google Docs exports).
Scanned or image-only resumes have no text to edit.
"""
import functools
import os
import re
import urllib.parse
import urllib.request

import pymupdf

BULLET_GLYPHS = "•●▪◦·"
BULLET_LEADS = BULLET_GLYPHS + "-–"
COLUMN_BUCKET = 20
MIN_SHRINK = 0.97
PARAGRAPH_MIN_LINES = 3
PARAGRAPH_MIN_AVG_CHARS = 35
WRAP_SLACK = 0.92

_WEIGHTS = {
    "thin": 100, "extralight": 200, "light": 300, "regular": 400, "book": 400, "medium": 500,
    "semibold": 600, "demibold": 600, "bold": 700, "extrabold": 800, "black": 900,
}


def _split_font_name(pdf_font: str):
    """'ABCDEF+Montserrat-SemiBoldItalic' -> ('Montserrat', italic=True, weight=600)"""
    name = pdf_font.split("+", 1)[-1]
    family, _, style = name.partition("-")
    style = style.lower()
    italic = "italic" in style or "oblique" in style
    style = style.replace("italic", "").replace("oblique", "") or "regular"
    family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", family)
    return family, italic, _WEIGHTS.get(style, 400)


def google_font_resolver(cache_dir: str):
    """Return a function mapping a PDF font name to TTF bytes from Google Fonts, or None."""
    os.makedirs(cache_dir, exist_ok=True)

    @functools.cache
    def resolve(pdf_font: str):
        family, italic, weight = _split_font_name(pdf_font)
        path = os.path.join(cache_dir, f"{family.replace(' ', '')}-{weight}{'i' if italic else ''}.ttf")
        if not os.path.exists(path):
            axis = f"ital,wght@{int(italic)},{weight}" if italic else f"wght@{weight}"
            css_url = f"https://fonts.googleapis.com/css2?family={urllib.parse.quote_plus(family)}:{axis}"
            try:
                css = urllib.request.urlopen(css_url, timeout=15).read().decode()
                ttf_url = re.search(r"url\((https://[^)]+\.ttf)\)", css).group(1)
                with open(path, "wb") as f:
                    f.write(urllib.request.urlopen(ttf_url, timeout=30).read())
            except Exception:
                return None
        with open(path, "rb") as f:
            return f.read()

    return resolve


def _column(x: float) -> int:
    return round(x / COLUMN_BUCKET)


def _lines(page):
    out = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            first = spans[0]
            out.append({
                "x": first["origin"][0], "y": first["origin"][1],
                "bbox": pymupdf.Rect(line["bbox"]),
                "text": " ".join(s["text"].strip() for s in spans),
                "font": first["font"], "size": first["size"], "color": first["color"],
                "mixed": len({(s["font"], round(s["size"], 1)) for s in spans}) > 1,
            })
    return out


def _bullet_dots(page):
    """Small round/square marks that repeat down a column. Icons (location pin, LinkedIn logo)
    contain small shapes too, but those appear once, so a mark must have a same-size sibling
    in the same column to count as a bullet."""
    marks = [d["rect"] for d in page.get_drawings()
             if 1.2 <= d["rect"].width <= 4.5 and abs(d["rect"].width - d["rect"].height) < 0.4]
    return [m for m in marks
            if any(o is not m and abs(o.x0 - m.x0) < 1 and abs(o.width - m.width) < 0.3 for o in marks)]


def _starts_bullet(line, dots, glyph_bullets):
    if line["text"][:1] in BULLET_LEADS:
        return True
    if any(abs(g.y1 - line["y"]) < 3 and 0 < line["x"] - g.x0 < 25 for g in glyph_bullets):
        return True
    return any(abs(d.y0 + d.height / 2 - (line["y"] - line["size"] * 0.33)) < line["size"] * 0.4
               and 0 < line["x"] - d.x1 < 25 for d in dots)


def _continues(prev, line):
    same_style = prev["font"] == line["font"] and abs(prev["size"] - line["size"]) < 0.1
    gap = line["y"] - prev["y"]
    return same_style and abs(prev["x"] - line["x"]) < 1.5 and 1.2 * line["size"] < gap < 2.1 * line["size"]


def find_blocks(pdf_path: str) -> list:
    """
    Group text lines into editable blocks. A block is a bullet (starts beside a bullet dot)
    or a paragraph of long lines. Headings, dates, contact lines and names are left out.
    """
    blocks = []
    with pymupdf.open(pdf_path) as doc:
        for page_no, page in enumerate(doc):
            lines = sorted(_lines(page), key=lambda l: (_column(l["x"]), l["y"], l["x"]))
            dots = _bullet_dots(page)
            glyph_bullets = [l["bbox"] for l in lines if l["text"] in BULLET_GLYPHS]
            column_right = {}
            for l in lines:
                column_right[_column(l["x"])] = max(column_right.get(_column(l["x"]), 0), l["bbox"].x1)

            groups = []
            for line in lines:
                if line["text"] in BULLET_GLYPHS:
                    continue
                is_bullet = _starts_bullet(line, dots, glyph_bullets)
                if groups and not is_bullet and _continues(groups[-1]["lines"][-1], line):
                    groups[-1]["lines"].append(line)
                else:
                    groups.append({"bullet": is_bullet, "lines": [line]})

            for g in groups:
                joined = " ".join(l["text"] for l in g["lines"])
                n_lines = len(g["lines"])
                is_paragraph = (n_lines >= PARAGRAPH_MIN_LINES
                                and len(joined) / n_lines >= PARAGRAPH_MIN_AVG_CHARS)
                if not (g["bullet"] or is_paragraph) or any(l["mixed"] for l in g["lines"]):
                    continue
                first = g["lines"][0]
                width = min(column_right[_column(first["x"])], page.rect.x1 + 3) - first["x"]
                text = joined.lstrip(BULLET_LEADS + " ")
                prefix = joined[:len(joined) - len(text)]
                char_width = sum(l["bbox"].width for l in g["lines"]) / len(joined)
                blocks.append({
                    "id": len(blocks),
                    "page": page_no,
                    "text": text,
                    "prefix": prefix,
                    "lines": g["lines"],
                    "font": first["font"], "size": first["size"], "color": first["color"],
                    "width": width,
                    "max_chars": max(int(width * n_lines / char_width * WRAP_SLACK), len(text)),
                })
    return blocks


def load_fonts(blocks: list, font_resolver) -> dict:
    """{pdf font name: pymupdf.Font or None} for every font used by the blocks."""
    fonts = {}
    for name in {b["font"] for b in blocks}:
        data = font_resolver(name)
        fonts[name] = pymupdf.Font(fontbuffer=data) if data else None
    return fonts


def _wrap(font, text, size, width):
    out, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if not current or font.text_length(trial, fontsize=size) <= width:
            current = trial
        else:
            out.append(current)
            current = word
    return out + ([current] if current else [])


def layout(block: dict, text: str, font) -> tuple:
    """Wrap text into the block's lines, at full size or slightly shrunk -> (wrapped_lines, size, fits)."""
    full = block["prefix"] + text
    for size in (block["size"], block["size"] * MIN_SHRINK):
        wrapped = _wrap(font, full, size, block["width"])
        if len(wrapped) <= len(block["lines"]):
            return wrapped, size, True
    return wrapped, size, False


def _numbers(text: str) -> set:
    return set(re.findall(r"\d+(?:[.,]\d+)*", text))


def check_edits(blocks: list, edits: dict, fonts: dict) -> tuple:
    """
    Split {block_id: new_text} into edits that can be written and rejected ones.
    Returns (plans, rejected): plans = {block_id: (wrapped_lines, size)}; each rejected entry is
    {"id", "old", "new", "reason"}, plus "lines_needed" / "lines_available" when it didn't fit.
    """
    by_id = {b["id"]: b for b in blocks}
    plans, rejected = {}, []
    for block_id, new_text in edits.items():
        block = by_id.get(block_id)
        new_text = " ".join((new_text or "").split())
        entry = {"id": block_id, "old": block["text"] if block else "", "new": new_text}
        if block is None or not new_text:
            rejected.append({**entry, "reason": "unknown block or empty text"})
        elif new_text == block["text"]:
            continue
        elif missing := sorted(_numbers(block["text"]) - _numbers(new_text)):
            rejected.append({**entry, "reason": f"dropped {', '.join(missing)} from the original"})
        elif fonts.get(block["font"]) is None:
            rejected.append({**entry, "reason": f"font '{block['font']}' is not available"})
        else:
            wrapped, size, fits = layout(block, new_text, fonts[block["font"]])
            if fits:
                plans[block_id] = (wrapped, size)
            else:
                rejected.append({**entry, "lines_needed": len(wrapped), "lines_available": len(block["lines"]),
                                 "reason": f"needs {len(wrapped)} lines, only {len(block['lines'])} available"})
    return plans, rejected


def apply_edits(pdf_path: str, blocks: list, edits: dict, fonts: dict, out_path: str) -> dict:
    """
    Write the edits that pass check_edits on the blocks' original lines, in their original font,
    size and colour. Returns {"applied": [{"id", "old", "new"}], "skipped": [rejected entries]}.
    """
    by_id = {b["id"]: b for b in blocks}
    plans, rejected = check_edits(blocks, edits, fonts)
    font_names = {}

    with pymupdf.open(pdf_path) as doc:
        for block_id in plans:
            block = by_id[block_id]
            for line in block["lines"]:
                band = pymupdf.Rect(line["bbox"].x0, line["y"] - line["size"] * 0.75,
                                    line["bbox"].x1, line["y"] + line["size"] * 0.2)
                doc[block["page"]].add_redact_annot(band)
        for page in doc:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                  text=pymupdf.PDF_REDACT_TEXT_REMOVE)

        for block_id, (wrapped, size) in plans.items():
            block = by_id[block_id]
            page = doc[block["page"]]
            key = (block["page"], block["font"])
            if key not in font_names:
                font_names[key] = f"cv{len(font_names)}"
                page.insert_font(fontname=font_names[key], fontbuffer=fonts[block["font"]].buffer)
            for line, text in zip(block["lines"], wrapped):
                page.insert_text((line["x"], line["y"]), text, fontname=font_names[key], fontsize=size,
                                 color=pymupdf.sRGB_to_pdf(block["color"]))

        doc.subset_fonts()
        doc.save(out_path, garbage=3, deflate=True)

    applied = [{"id": i, "old": by_id[i]["text"], "new": " ".join(edits[i].split())} for i in plans]
    return {"applied": applied, "skipped": rejected}


def render_pages(pdf_bytes: bytes, dpi: int = 110) -> list:
    """PNG bytes for each page, for previews."""
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [page.get_pixmap(dpi=dpi).tobytes("png") for page in doc]
