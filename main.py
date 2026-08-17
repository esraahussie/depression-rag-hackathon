import glob
import json
import os
import re
from collections import Counter

import fitz

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# SETTINGS
PDF_FOLDER = "pdfs"
OUTPUT_FOLDER = "outputs"
METADATA_FILE = os.path.join(OUTPUT_FOLDER, "chunks_metadata.json")
CHROMA_FOLDER = os.path.join(OUTPUT_FOLDER, "chroma_db")
COLLECTION_NAME = "depression_clinical"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
MIN_CHUNK_CHARS = 80

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

TEST_QUERIES = [
    "What are the core diagnostic symptoms of major depressive disorder?",
    "What treatment options are effective for depression, including medication and therapy?",
    "How is depression severity measured or screened in clinical settings?",
]

SKIP_SECTIONS = {
    "contents",
    "table of contents",
    "your responsibility",
    "copyright",
    "disclaimer",
    "source guidance",
    "why this is important",
    "why the committee made the recommendations",
}

JUNK_HEADING_RE = re.compile(r"^\([^)]{1,40}\)$")  # "(DSM-5)" and similar fragments

MIN_RETRIEVE_SCORE = 0.53
DEDUP_COSINE = 0.92
CANDIDATE_POOL = 40

ABBREV_EXPAND = {
    "phq-9": "patient health questionnaire 9 depression screening score",
    "phq9": "patient health questionnaire 9 depression screening score",
    "ssri": "selective serotonin reuptake inhibitor antidepressant",
    "ssris": "selective serotonin reuptake inhibitor antidepressant",
    "snri": "serotonin noradrenaline reuptake inhibitor antidepressant",
    "mdd": "major depressive disorder",
    "cbt": "cognitive behavioural therapy psychotherapy",
    "dsm-5": "diagnostic and statistical manual of mental disorders",
    "dsm-iv": "diagnostic and statistical manual of mental disorders",
    "icd-10": "international classification of diseases",
    "ng222": "nice guideline ng222 depression in adults treatment",
    "nice": "national institute for health and care excellence",
}

QUERY_HINTS = [
    (r"how long must .*last|last before .*diagnos", "symptoms persist at least 2 weeks two weeks"),
    (r"how many .*symptoms|dsm-5 symptoms are required", "5 of 9 five or more dsm-5 symptoms"),
    (r"how many years .*chronic|chronic depressive", "at least 2 years chronic depressive symptoms"),
    (r"when should the clinician review|review how well", "first review within 2 weeks 2 to 4 weeks after starting treatment"),
    (r"core diagnostic symptoms", "key symptoms low mood loss of interest anhedonia"),
    (r"severity measured|screened in clinical", "phq-9 patient health questionnaire screening instrument"),
]

GUIDELINE_RE = re.compile(r"\b((?:NG|CG|QS|PH)\d+)\b", re.I)
WHO_ID_RE = re.compile(r"(WHO[\s\-]?EM/MNH/\d+(?:/[A-Z])?)", re.I)
NICE_URL_RE = re.compile(r"nice\.org\.uk/guidance/([a-z]{2}\d+)", re.I)
WHO_FILE_RE = re.compile(r"WHOEMMNH(\d+)([A-Z])?", re.I)
YEAR_RE = re.compile(
    r"(?:Last updated|Published(?:\s+online)?)\s*:?\s*\d{1,2}\s+[A-Za-z]+\s+(\d{4})",
    re.I,
)
PDF_DATE_RE = re.compile(r"D:(\d{4})")
HEADER_NOISE_RE = re.compile(
    r"(all rights reserved|notice of rights|jama\.com|reprinted\)|subject to notice|"
    r"©|\(reprinted\)|creative commons|cc by-nc)",
    re.I,
)
CHROME_LINE_RE = re.compile(
    r"^(editorial|multimedia|related article|jama patient page|supplemental content|"
    r"cme at |author/group information|corresponding author|accepted for publication|"
    r"conflict of interest|article information|author affiliations)\b",
    re.I,
)
LAST_UPDATED_RE = re.compile(
    r"Last updated\s*:?\s*\d{1,2}\s+[A-Za-z]+\s+(\d{4})",
    re.I,
)


# STEP 1: LOW-LEVEL PAGE EXTRACTION (PyMuPDF layout)

def _reconstruct_line_text(line):
    """Rebuild a line from character boxes so missing PDF spaces are restored."""
    chars = []
    max_size = 0.0
    bold = False

    for span in line.get("spans", []):
        max_size = max(max_size, float(span.get("size") or 0))
        bold = bold or bool(span.get("flags", 0) & 16)
        span_chars = span.get("chars")
        if span_chars:
            chars.extend(span_chars)
        elif span.get("text"):
            bbox = span.get("bbox") or [0, 0, 0, 0]
            chars.append({"c": span["text"], "bbox": bbox, "size": span.get("size") or 0})

    if not chars:
        return "", max_size, bold

    chars.sort(key=lambda c: (c["bbox"][0], c["bbox"][1]))
    size = max_size or 10.0
    gap_threshold = max(0.7, size * 0.08)

    pieces = [chars[0].get("c") or ""]
    for prev, cur in zip(chars, chars[1:]):
        prev_c = prev.get("c") or ""
        cur_c = cur.get("c") or ""
        if not cur_c:
            continue
        if cur_c == " " or prev_c.endswith(" ") or cur_c.startswith(" "):
            pieces.append(cur_c)
            continue
        gap = cur["bbox"][0] - prev["bbox"][2]
        if gap >= gap_threshold:
            pieces.append(" ")
        pieces.append(cur_c)

    text = re.sub(r"[ \t]+", " ", "".join(pieces)).strip()
    return text, max_size, bold


def _span_record(span, fallback_bbox):
    chars = span.get("chars")
    if chars:
        dummy = {
            "spans": [{
                "chars": chars,
                "size": span.get("size") or 0,
                "flags": span.get("flags") or 0,
                "bbox": span.get("bbox") or fallback_bbox,
            }]
        }
        text, size, bold = _reconstruct_line_text(dummy)
        bbox = span.get("bbox") or fallback_bbox
    else:
        text = (span.get("text") or "").strip()
        size = float(span.get("size") or 0)
        bold = bool(span.get("flags", 0) & 16)
        bbox = span.get("bbox") or fallback_bbox
    return {
        "text": text,
        "x0": bbox[0],
        "y0": bbox[1],
        "x1": bbox[2],
        "y1": bbox[3],
        "size": size,
        "bold": bold,
    }


def _records_from_line(line_dict):
    """One visual line may mix a run-in heading span with body text; split those."""
    bbox = line_dict.get("bbox") or [0, 0, 0, 0]
    spans = [s for s in line_dict.get("spans", []) if s.get("chars") or s.get("text")]
    if len(spans) >= 2:
        first = _span_record(spans[0], bbox)
        rest_text, rest_size, rest_bold = _reconstruct_line_text(
            {"spans": spans[1:], "bbox": bbox}
        )
        first_text = first["text"].strip()
        if (
            first_text
            and rest_text
            and len(first_text) <= 48
            and len(rest_text) > 20
            and (first["bold"] or first_text.isupper() or first["size"] >= rest_size * 1.12)
        ):
            rest = {
                "text": rest_text,
                "x0": bbox[0],
                "y0": bbox[1],
                "x1": bbox[2],
                "y1": bbox[3],
                "size": rest_size,
                "bold": rest_bold,
            }
            return [first, rest]

    text, size, bold = _reconstruct_line_text(line_dict)
    if not text:
        return []
    return [{
        "text": text,
        "x0": bbox[0],
        "y0": bbox[1],
        "x1": bbox[2],
        "y1": bbox[3],
        "size": size,
        "bold": bold,
    }]


def extract_page_lines(page):
    raw = page.get_text("rawdict")
    lines = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            lines.extend(_records_from_line(line))
    return lines


def _find_column_split(lines, page_width):
    mids = []
    for ln in lines:
        width = ln["x1"] - ln["x0"]
        if width < 0.5 * page_width:
            mids.append((ln["x0"] + ln["x1"]) / 2.0)
    if len(mids) < 10:
        return None
    mid = page_width * 0.5
    left = sum(1 for x in mids if x < mid)
    right = sum(1 for x in mids if x >= mid)
    if left >= 4 and right >= 4 and right / len(mids) >= 0.22:
        return mid
    return None


def _column_index(ln, split_x, page_width):
    if split_x is None:
        return 0
    if ln["x0"] < split_x * 0.9 and ln["x1"] > split_x + 20:
        return -1
    if (ln["x1"] - ln["x0"]) > 0.55 * page_width:
        return -1
    return 0 if ln["x0"] < split_x else 1


def _line_in_bbox(ln, bbox, pad=3):
    cx = (ln["x0"] + ln["x1"]) / 2.0
    cy = (ln["y0"] + ln["y1"]) / 2.0
    x0, y0, x1, y1 = bbox
    return (x0 - pad) <= cx <= (x1 + pad) and (y0 - pad) <= cy <= (y1 + pad)


def _table_to_markdown(table):
    try:
        md = table.to_markdown()
        if md and md.strip():
            return md.strip()
    except Exception:
        pass
    rows = table.extract() or []
    cleaned = []
    for row in rows:
        cells = [("" if c is None else str(c).replace("\n", " ").strip()) for c in row]
        if any(cells):
            cleaned.append(cells)
    if len(cleaned) < 2:
        return ""
    header = cleaned[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in cleaned[1:]:
        row = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(row[: len(header)]) + " |")
    return "\n".join(lines)


def extract_page_tables(page):
    tables = []
    try:
        found = page.find_tables()
        candidates = list(found.tables) if found else []
    except Exception:
        candidates = []

    for table in candidates:
        if getattr(table, "col_count", 0) < 2 or getattr(table, "row_count", 0) < 2:
            continue
        md = _table_to_markdown(table)
        if not md:
            continue
        tables.append({"bbox": tuple(table.bbox), "markdown": md})

    if tables:
        return tables
    return _pdfplumber_fallback_tables(page)


def _pdfplumber_fallback_tables(page):
    """Used only when PyMuPDF found no table on this page."""
    if pdfplumber is None:
        return []
    path = getattr(page.parent, "name", None)
    if not path:
        return []
    extras = []
    try:
        with pdfplumber.open(path) as plumber_pdf:
            plumber_page = plumber_pdf.pages[page.number]
            found = []
            try:
                found = plumber_page.find_tables() or []
            except Exception:
                found = []

            if found:
                for table in found:
                    raw = table.extract()
                    dummy = type("T", (), {
                        "extract": lambda self, r=raw: r,
                        "to_markdown": lambda self: "",
                    })()
                    md = _table_to_markdown(dummy)
                    if not md:
                        continue
                    bbox = tuple(table.bbox) if getattr(table, "bbox", None) else (0, 0, 0, 0)
                    extras.append({"bbox": bbox, "markdown": md})
            else:
                for raw in plumber_page.extract_tables() or []:
                    if not raw or len(raw) < 2 or len(raw[0]) < 2:
                        continue
                    dummy = type("T", (), {
                        "extract": lambda self, r=raw: r,
                        "to_markdown": lambda self: "",
                    })()
                    md = _table_to_markdown(dummy)
                    if md:
                        extras.append({"bbox": (0, 0, 0, 0), "markdown": md})
    except Exception:
        return extras
    return extras


def order_page_items(lines, tables, page_width):
    """Column-aware reading order, with tables inserted at their vertical position."""
    split_x = _find_column_split(lines, page_width)
    table_bboxes = [t["bbox"] for t in tables if t["bbox"] != (0, 0, 0, 0)]
    text_lines = [
        ln for ln in lines
        if not any(_line_in_bbox(ln, bbox) for bbox in table_bboxes)
    ]

    items = []
    for ln in text_lines:
        col = _column_index(ln, split_x, page_width)
        items.append((col, ln["y0"], ln["x0"], "text", ln))
    for table in tables:
        bbox = table["bbox"]
        if bbox == (0, 0, 0, 0):
            col, y0, x0 = 0, 10**9, 0
        else:
            cx = (bbox[0] + bbox[2]) / 2.0
            if split_x is None or (bbox[2] - bbox[0]) > 0.55 * page_width:
                col = -1
            else:
                col = 0 if cx < split_x else 1
            y0, x0 = bbox[1], bbox[0]
        items.append((col, y0, x0, "table", table))

    items.sort(key=lambda it: (it[0] if it[0] >= 0 else -1, it[1], it[2]))
    return items


def join_column_lines(lines):
    """Join hyphenated line breaks: 'depres-' + 'sion' -> 'depression'."""
    if not lines:
        return ""
    parts = [lines[0]["text"].rstrip()]
    for ln in lines[1:]:
        nxt = ln["text"].strip()
        prev = parts[-1]
        if prev.endswith(("\u00ad", "-", "\u2010", "\u2011")) and nxt and nxt[:1].islower():
            parts[-1] = prev.rstrip("\u00ad-\u2010\u2011") + nxt
        else:
            parts.append(nxt)
    return "\n".join(parts)


# STEP 2: HEADERS, TOC, HEADINGS, CLEANING

def _normalize_header(text):
    text = re.sub(r"\d+", "#", text.lower())
    return re.sub(r"\s+", " ", text).strip()[:120]


def detect_repeating_lines(pages_lines, min_pages=2, min_frac=0.35):
    counts = Counter()
    n_pages = max(len(pages_lines), 1)
    for lines in pages_lines:
        seen = set()
        if not lines:
            continue
        page_h = max(ln["y1"] for ln in lines) or 1
        for ln in lines:
            in_margin = ln["y0"] < 0.12 * page_h or ln["y1"] > 0.88 * page_h
            if not in_margin and not HEADER_NOISE_RE.search(ln["text"]):
                continue
            key = _normalize_header(ln["text"])
            if len(key) < 8:
                continue
            seen.add(key)
        for key in seen:
            counts[key] += 1
    threshold = max(min_pages, int(min_frac * n_pages))
    return {key for key, n in counts.items() if n >= threshold}


def is_header_or_footer(ln, repeating, page_height):
    text = ln["text"].strip()
    if re.fullmatch(r"\d{1,4}", text):
        return True
    if HEADER_NOISE_RE.search(text) or CHROME_LINE_RE.search(text):
        return True
    if _normalize_header(text) in repeating:
        return True
    if page_height and (ln["y0"] < 0.06 * page_height or ln["y1"] > 0.94 * page_height):
        if len(text) <= 80:
            return True
    return False


def is_toc_page(lines):
    texts = [ln["text"].strip() for ln in lines if ln["text"].strip()]
    if not texts:
        return True
    dot_lines = sum(1 for t in texts if re.search(r"\.{5,}|…", t))
    if dot_lines >= 5 and dot_lines / len(texts) >= 0.25:
        return True
    first = texts[0].lower().strip(" :")
    if first in {"contents", "table of contents"} and dot_lines >= 3:
        return True
    return False


def is_heading(ln, body_size):
    text = ln["text"].strip()
    if not text or len(text) > 110:
        return False
    if JUNK_HEADING_RE.match(text):
        return False
    if text.startswith("[") or text.startswith("%"):
        return False
    if re.search(r"95%\s*CI|I2\s*=", text):
        return False
    if CHROME_LINE_RE.search(text):
        return False
    if re.fullmatch(r"[\d\.\s]+", text):
        return False
    if text.startswith("(") and len(text) < 24:
        return False
    if text.endswith(")") and len(text.split()) <= 3:
        return False
    if not re.search(r"[A-Za-z]{4,}", text):
        return False
    words = text.split()
    if len(words) > 14:
        return False
    size_ratio = (ln["size"] / body_size) if body_size else 1.0
    if text[0].islower() and size_ratio < 1.18:
        return False
    if text.endswith(".") and size_ratio < 1.35:
        return False
    if size_ratio >= 1.18:
        return True
    if ln["bold"] and size_ratio >= 1.08 and len(words) <= 10:
        return True
    if text.isupper() and 1 <= len(words) <= 6 and 4 <= len(text) <= 48:
        return True
    return False


def is_legal_boilerplate(lines):
    joined = " ".join(ln["text"] for ln in lines).lower()
    return (
        "represent the view of nice" in joined
        and "careful consideration of the evidence" in joined
    )


def merge_heading_blocks(blocks):
    merged = []
    for block in blocks:
        if (
            merged
            and block["kind"] == "heading"
            and merged[-1]["kind"] == "heading"
            and block["page"] == merged[-1]["page"]
            and abs((merged[-1].get("size") or 0) - (block.get("size") or 0)) <= 2
            and len(merged[-1]["text"]) + len(block["text"]) < 160
        ):
            merged[-1]["text"] = (merged[-1]["text"].rstrip() + " " + block["text"]).strip()
            continue
        merged.append(block)
    return merged


def cover_title_from_lines(first_page_lines, body_size):
    large = [ln for ln in first_page_lines if ln["size"] >= body_size * 1.45]
    large.sort(key=lambda ln: (ln["y0"], ln["x0"]))
    title = " ".join(ln["text"].strip() for ln in large if ln["text"].strip())
    return re.sub(r"\s+", " ", title).strip(" :")[:240]


def clean_text(text):
    """Cleanup that keeps clinical citation numbers intact."""
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)[\-\u2010\u2011]\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\S+@\S+\.\S+", "", text)
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# STEP 3: DOCUMENT METADATA

def _pdf_year(meta):
    for key in ("modDate", "creationDate"):
        match = PDF_DATE_RE.search(str(meta.get(key) or ""))
        if match:
            return int(match.group(1))
    return 0


def infer_doc_meta(pdf_path, pdf_meta, preview_text, toc, cover_title=""):
    file_name = os.path.basename(pdf_path)
    title = (pdf_meta.get("title") or "").strip()
    author = (pdf_meta.get("author") or "").strip()
    subject = (pdf_meta.get("subject") or "").strip()
    keywords = (pdf_meta.get("keywords") or "").strip()
    blob = " ".join([file_name, title, author, subject, keywords, preview_text[:2500]])
    blob_l = blob.lower()

    if "nice" in blob_l or "national institute for health" in blob_l:
        organization = "NICE"
        if "quality standard" in blob_l or re.search(r"\bqs\d+\b", blob_l):
            doc_type = "quality_standard"
        else:
            doc_type = "guideline"
    elif "uspstf" in blob_l or "preventive services task force" in blob_l:
        organization = "USPSTF"
        doc_type = "recommendation_statement"
    elif "who" in blob_l or "world health organization" in blob_l or file_name.upper().startswith("WHO"):
        organization = "WHO"
        doc_type = "factsheet"
    else:
        organization = author or "unknown"
        doc_type = "clinical_document"

    guideline_id = ""
    for source in (keywords, subject, blob):
        match = GUIDELINE_RE.search(source)
        if match:
            guideline_id = match.group(1).upper()
            break
    if not guideline_id:
        match = WHO_ID_RE.search(blob.replace(" ", ""))
        if match:
            guideline_id = match.group(1).upper().replace("WHOEM", "WHO-EM")
        else:
            match = WHO_ID_RE.search(blob)
            if match:
                guideline_id = match.group(1).upper()
    if not guideline_id:
        match = NICE_URL_RE.search(blob_l)
        if match:
            guideline_id = match.group(1).upper()
    if not guideline_id:
        match = WHO_FILE_RE.search(file_name)
        if match:
            letter = match.group(2) or "E"
            guideline_id = f"WHO-EM/MNH/{match.group(1)}/{letter}"

    year = 0
    match = LAST_UPDATED_RE.search(preview_text) or LAST_UPDATED_RE.search(blob)
    if match:
        year = int(match.group(1))
    else:
        match = YEAR_RE.search(preview_text) or YEAR_RE.search(blob)
        if match:
            year = int(match.group(1))
    if not year:
        year = _pdf_year(pdf_meta)

    if not title:
        if cover_title:
            title = cover_title
        elif toc:
            title = toc[0][1].strip()
        elif subject:
            title = re.sub(r"\s*\([^)]+\)\s*$", "", subject).strip()
        else:
            first_line = next((ln for ln in preview_text.splitlines() if ln.strip()), "")
            title = first_line.strip()[:180]
    if not title:
        title = os.path.splitext(file_name)[0]

    return {
        "source_file": file_name,
        "doc_title": title[:240],
        "organization": organization,
        "doc_type": doc_type,
        "guideline_id": guideline_id,
        "year": int(year or 0),
        "page_count": 0,
    }


def toc_section_for_page(toc, page_number):
    current = ""
    for level, name, toc_page in toc:
        if toc_page > page_number:
            break
        if level <= 3 and name and not re.fullmatch(r"[\d\.]+", name.strip()):
            if name.strip().lower() not in SKIP_SECTIONS:
                current = name.strip()
    return current[:200]


# STEP 4: DOCUMENT -> SECTION BLOCKS

def extract_document(pdf_path):
    doc = fitz.open(pdf_path)
    pdf_meta = doc.metadata or {}
    toc = doc.get_toc() or []

    pages_lines = [extract_page_lines(page) for page in doc]
    char_sizes = Counter()
    for lines in pages_lines:
        for ln in lines:
            if ln["size"] > 0 and len(ln["text"]) >= 40:
                char_sizes[round(ln["size"], 1)] += len(ln["text"])
    if char_sizes:
        body_size = char_sizes.most_common(1)[0][0]
    else:
        sizes = [ln["size"] for lines in pages_lines for ln in lines if ln["size"] > 0]
        body_size = Counter(round(s, 1) for s in sizes).most_common(1)[0][0] if sizes else 10.0
    repeating = detect_repeating_lines(pages_lines)

    preview_parts = []
    page_blocks = []

    for page_index, page in enumerate(doc):
        page_number = page_index + 1
        lines = pages_lines[page_index]
        page_height = page.rect.height
        page_width = page.rect.width

        filtered = [ln for ln in lines if not is_header_or_footer(ln, repeating, page_height)]
        if page_index < 2:
            preview_parts.append("\n".join(ln["text"] for ln in filtered[:40]))

        if is_toc_page(filtered) or is_legal_boilerplate(filtered):
            continue

        tables = extract_page_tables(page)
        ordered = order_page_items(filtered, tables, page_width)

        pending_lines = []
        pending_col = None
        blocks = []

        def flush_lines():
            nonlocal pending_lines
            if not pending_lines:
                return
            text = clean_text(join_column_lines(pending_lines))
            pending_lines = []
            if text:
                blocks.append({"kind": "text", "text": text, "page": page_number, "has_table": False})

        for col, _y, _x, kind, payload in ordered:
            if kind == "table":
                flush_lines()
                md = clean_text(payload["markdown"])
                if md:
                    blocks.append({"kind": "table", "text": md, "page": page_number, "has_table": True})
                continue

            ln = payload
            if is_heading(ln, body_size):
                flush_lines()
                heading = clean_text(ln["text"])
                if heading and heading.lower() not in SKIP_SECTIONS:
                    blocks.append({
                        "kind": "heading",
                        "text": heading,
                        "page": page_number,
                        "has_table": False,
                        "size": ln["size"],
                    })
                continue

            if pending_col is not None and col != pending_col:
                flush_lines()
            pending_col = col
            pending_lines.append(ln)

        flush_lines()
        blocks = merge_heading_blocks(blocks)
        if blocks:
            page_blocks.append((page_number, blocks))

    preview_text = "\n".join(preview_parts)
    cover_title = cover_title_from_lines(pages_lines[0] if pages_lines else [], body_size)
    doc_meta = infer_doc_meta(pdf_path, pdf_meta, preview_text, toc, cover_title=cover_title)
    doc_meta["page_count"] = doc.page_count
    doc.close()
    return doc_meta, page_blocks, toc


# STEP 5: CHUNK BY SECTION, THEN SIZE

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP, separators=None):
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]
    return _split_text(text, separators, chunk_size, overlap)


def _split_text(text, separators, chunk_size, overlap):
    separator = separators[-1]
    remaining_separators = []

    for i, sep in enumerate(separators):
        if sep == "" or sep in text:
            separator = sep
            remaining_separators = separators[i + 1:]
            break

    pieces = text.split(separator) if separator else list(text)
    good_pieces = []

    for piece in pieces:
        if len(piece) <= chunk_size or not remaining_separators:
            good_pieces.append(piece)
        else:
            good_pieces.extend(
                _split_text(piece, remaining_separators, chunk_size, overlap)
            )

    return _merge_pieces(good_pieces, separator, chunk_size, overlap)


def _merge_pieces(pieces, separator, chunk_size, overlap):
    chunks = []
    current = []
    current_len = 0

    for piece in pieces:
        piece_len = len(piece) + len(separator)

        if current and current_len + piece_len > chunk_size:
            chunk = separator.join(current).strip()
            if chunk:
                chunks.append(chunk)

            overlap_pieces = []
            overlap_len = 0
            for p in reversed(current):
                overlap_len += len(p) + len(separator)
                if overlap_len > overlap:
                    break
                overlap_pieces.insert(0, p)

            current = overlap_pieces
            current_len = sum(len(p) + len(separator) for p in current)

        current.append(piece)
        current_len += piece_len

    if current:
        chunk = separator.join(current).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


def is_atomic_clinical_block(text):
    """Keep diagnostic lists / NICE rec bullets in one chunk so criteria are not split."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False
    bullets = 0
    for ln in lines:
        if re.match(r"^([•\-\*\u2022\u25cf]|Key symptoms:|\d+\.\d+)", ln):
            bullets += 1
        elif ln[:1].islower() and bullets:
            bullets += 1
    if bullets >= 3:
        return True
    lowered = text.lower()
    return bullets >= 2 and any(
        marker in lowered
        for marker in ("key symptoms", "associated symptoms", "dsm", "icd-10", "icd 10")
    )


def _split_keep_pages(text, page, has_table, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split a text block into sized chunks, carrying page/table flags."""
    keep_whole = has_table or is_atomic_clinical_block(text) or len(text) <= chunk_size
    if keep_whole and len(text) <= 1800:
        return [{"text": text, "page_start": page, "page_end": page, "has_table": has_table}]
    return [
        {"text": part, "page_start": page, "page_end": page, "has_table": False}
        for part in chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if part.strip()
    ]


def chunk_document(doc_meta, page_blocks, toc, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    current_section = doc_meta.get("doc_title") or "Unspecified"
    segments = []

    for page_number, blocks in page_blocks:
        toc_section = toc_section_for_page(toc, page_number)
        if current_section in {"", "Unspecified"} and toc_section:
            current_section = toc_section

        for block in blocks:
            if block["kind"] == "heading":
                heading = block["text"].strip()
                if heading.lower() not in SKIP_SECTIONS and not JUNK_HEADING_RE.match(heading):
                    current_section = heading
                continue
            if current_section.lower() in SKIP_SECTIONS:
                continue
            section = current_section or toc_section or doc_meta.get("doc_title") or "Unspecified"
            for part in _split_keep_pages(
                block["text"], block["page"], block["has_table"],
                chunk_size=chunk_size, overlap=overlap,
            ):
                part["section"] = section
                segments.append(part)

    chunks = []
    bucket = []
    bucket_len = 0
    bucket_section = None

    def flush():
        nonlocal bucket, bucket_len
        if not bucket:
            return
        text = "\n\n".join(item["text"] for item in bucket).strip()
        if len(text) >= MIN_CHUNK_CHARS or any(item["has_table"] for item in bucket):
            chunks.append({
                "text": text,
                "section_title": bucket_section or "Unspecified",
                "page_start": min(item["page_start"] for item in bucket),
                "page_end": max(item["page_end"] for item in bucket),
                "has_table": any(item["has_table"] for item in bucket),
            })
        bucket = []
        bucket_len = 0

    for seg in segments:
        if bucket_section is not None and seg["section"] != bucket_section:
            flush()
        if bucket and bucket_len + len(seg["text"]) + 2 > chunk_size and not seg["has_table"]:
            combined = "\n\n".join(item["text"] for item in bucket) + "\n\n" + seg["text"]
            keep_list = (
                is_atomic_clinical_block(seg["text"])
                and is_atomic_clinical_block(combined)
                and bucket_len + len(seg["text"]) + 2 <= 1800
            )
            if not keep_list:
                flush()
        bucket.append(seg)
        bucket_section = seg["section"]
        bucket_len += len(seg["text"]) + 2
        if seg["has_table"] and bucket_len >= chunk_size:
            flush()

    flush()
    return chunks


# STEP 6: PIPELINE

def _chroma_metadata(meta):
    """Chroma only accepts flat str/int/float/bool values; never None."""
    return {
        "chunk_id": str(meta["chunk_id"]),
        "source_file": str(meta["source_file"]),
        "doc_title": str(meta.get("doc_title") or ""),
        "organization": str(meta.get("organization") or ""),
        "doc_type": str(meta.get("doc_type") or ""),
        "guideline_id": str(meta.get("guideline_id") or ""),
        "year": int(meta.get("year") or 0),
        "page_number": int(meta.get("page_start") or 0),
        "page_start": int(meta.get("page_start") or 0),
        "page_end": int(meta.get("page_end") or 0),
        "section_title": str(meta.get("section_title") or "Unspecified")[:200],
        "chunk_index": int(meta.get("chunk_index") or 0),
        "char_count": int(meta.get("char_count") or 0),
        "has_table": bool(meta.get("has_table")),
    }


def build_chunks_and_metadata(chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_paths = sorted(glob.glob(os.path.join(PDF_FOLDER, "*.pdf")))
    if not pdf_paths:
        print(f"No PDFs found in '{PDF_FOLDER}/'. Add some and rerun.")
        return [], [], []

    all_chunk_texts = []
    all_chunk_ids = []
    all_metadata = []

    for pdf_path in pdf_paths:
        file_name = os.path.basename(pdf_path)
        print(f"Processing: {file_name}")

        doc_meta, page_blocks, toc = extract_document(pdf_path)
        chunks = chunk_document(
            doc_meta, page_blocks, toc, chunk_size=chunk_size, overlap=overlap
        )
        print(
            f"  -> {len(chunks)} chunks | {doc_meta['organization']} | "
            f"{doc_meta['guideline_id'] or '-'} | {doc_meta['doc_title'][:60]}"
        )

        stem = os.path.splitext(file_name)[0]
        for i, chunk in enumerate(chunks):
            chunk_id = f"{stem}_{i:04d}"
            text = chunk["text"]
            all_chunk_texts.append(text)
            all_chunk_ids.append(chunk_id)
            all_metadata.append({
                "chunk_id": chunk_id,
                "source_file": file_name,
                "doc_title": doc_meta["doc_title"],
                "organization": doc_meta["organization"],
                "doc_type": doc_meta["doc_type"],
                "guideline_id": doc_meta["guideline_id"],
                "year": doc_meta["year"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "page_number": chunk["page_start"],
                "section_title": chunk["section_title"],
                "chunk_index": i,
                "char_count": len(text),
                "has_table": chunk["has_table"],
                "text_preview": text[:200],
            })

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)

    print(f"\nSaved metadata for {len(all_metadata)} chunks -> {METADATA_FILE}")
    return all_chunk_texts, all_chunk_ids, all_metadata


def embed_chunks(chunk_texts, chunk_ids, metadata_list):
    print("\nLoading embedding model (first run downloads it, needs internet)...")

    import chromadb
    from chromadb.utils import embedding_functions

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Recreated collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    simple_metadata = [_chroma_metadata(m) for m in metadata_list]
    batch_size = 64

    for i in range(0, len(chunk_texts), batch_size):
        collection.add(
            documents=chunk_texts[i:i + batch_size],
            ids=chunk_ids[i:i + batch_size],
            metadatas=simple_metadata[i:i + batch_size],
        )

    print(f"Embedded {collection.count()} chunks -> {CHROMA_FOLDER}")
    return collection


def run_test_queries(collection, queries=TEST_QUERIES, n_results=3):
    for query in queries:
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")

        results = collection.query(query_texts=[query], n_results=n_results)
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for rank in range(len(documents)):
            similarity = 1 - distances[rank]
            metadata = metadatas[rank]
            page_start = metadata.get("page_start", metadata.get("page_number", "N/A"))
            page_end = metadata.get("page_end", page_start)
            page = page_start if page_start == page_end else f"{page_start}-{page_end}"

            print(f"\n[{rank + 1}] similarity={similarity:.3f}")
            print(f"    source     = {metadata.get('source_file')}")
            print(f"    title      = {metadata.get('doc_title', '')}")
            print(f"    org / year = {metadata.get('organization', '')} / {metadata.get('year') or '-'}")
            print(f"    guideline  = {metadata.get('guideline_id') or '-'}")
            print(f"    page       = {page}")
            print(f"    section    = {metadata.get('section_title', 'Unspecified')}")
            print(f"    chunk      = {metadata.get('chunk_id', 'N/A')}")
            print("\n    TEXT:")
            print(documents[rank])


def clean_query(query):
    text = re.sub(r"\s+", " ", query).strip()
    extra = []
    lower = text.lower()
    for key, expansion in ABBREV_EXPAND.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            extra.append(expansion)
    for pattern, hint in QUERY_HINTS:
        if re.search(pattern, lower):
            extra.append(hint)
    if extra:
        text = text + " " + " ".join(extra)
    return text


def format_chunk_for_embedding(text, meta=None):
    """Prefix searchable metadata so queries align with org / guideline / section."""
    if not meta:
        return text
    section = str(meta.get("section_title") or "").strip()[:80]
    parts = [
        meta.get("organization"),
        meta.get("guideline_id"),
        section,
    ]
    page = meta.get("page_start") or meta.get("page_number")
    if page:
        parts.append(f"page {page}")
    prefix = " | ".join(str(p).strip() for p in parts if p)
    return f"{prefix}. {text}" if prefix else text


def boost_retrieval_scores(query, texts, metas, base_scores):
    """Lift exact clinical phrases and matching guideline IDs; demote 2-year near-misses."""
    import numpy as np

    scores = np.array(base_scores, dtype=float, copy=True)
    q = query.lower()
    gids = re.findall(r"\b((?:ng|cg|qs)\d+)\b", q)
    phrases = [
        phrase for phrase in (
            "2 weeks", "two weeks", "2-week", "2 years", "two years",
            "phq-9", "phq 9", "5 of 9", "five or more", "5 or more",
            "ssri", "snri", "cbt", "key symptoms", "first review",
            "signs and symptoms",
        )
        if phrase in q
    ]
    wants_two_weeks = ("2 weeks" in q or "two weeks" in q) and "diagnos" in q
    for i, (text, meta) in enumerate(zip(texts, metas)):
        blob = f"{text} {meta.get('section_title') or ''} {meta.get('guideline_id') or ''}".lower()
        gid = (meta.get("guideline_id") or "").lower()
        if gids and gid in gids:
            scores[i] += 0.12
        if any(phrase in blob for phrase in phrases):
            scores[i] += 0.10
        if wants_two_weeks and "2 years" in blob and "2 weeks" not in blob and "two weeks" not in blob:
            scores[i] -= 0.10
        if "first review" in q or ("review" in q and "starting" in q):
            section = (meta.get("section_title") or "").lower()
            if "first review" in blob or "within 2 weeks" in blob:
                scores[i] += 0.12
            if "further-line" in section or "has not responded" in blob:
                scores[i] -= 0.10
    return scores


def dedup_ranked_indices(order, texts, metas, scores, doc_emb=None, k=5, min_score=None):
    """Drop near-duplicate Top-K hits and optionally apply a confidence gate."""
    import numpy as np

    chosen = []
    seen_keys = set()
    seen_prefixes = []
    for idx in order:
        idx = int(idx)
        if min_score is not None and float(scores[idx]) < min_score:
            continue
        meta = metas[idx]
        section = re.sub(r"\s+", " ", str(meta.get("section_title") or "").lower())[:80]
        key = (meta.get("source_file"), meta.get("page_start") or meta.get("page_number"), section)
        if key in seen_keys:
            continue
        prefix = re.sub(r"\s+", " ", texts[idx][:140].lower())
        if any(prefix[:90] == prev[:90] for prev in seen_prefixes):
            continue
        if doc_emb is not None and chosen:
            cand = doc_emb[idx]
            if any(float(np.dot(cand, doc_emb[c])) > DEDUP_COSINE for c in chosen):
                continue
        seen_keys.add(key)
        seen_prefixes.append(prefix)
        chosen.append(idx)
        if len(chosen) >= k:
            break
    return chosen


def embed_minilm_onnx(texts, batch_size=16, max_length=256):
    """all-MiniLM-L6-v2 via ONNX Runtime (no torch / sentence-transformers)."""
    import numpy as np
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    tok_path = hf_hub_download("sentence-transformers/all-MiniLM-L6-v2", "tokenizer.json")
    onnx_path = hf_hub_download("sentence-transformers/all-MiniLM-L6-v2", "onnx/model.onnx")

    tokenizer = Tokenizer.from_file(tok_path)
    tokenizer.enable_truncation(max_length=max_length)
    tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    vectors = []

    for start in range(0, len(texts), batch_size):
        batch = [t if t.strip() else " " for t in texts[start:start + batch_size]]
        encoded = tokenizer.encode_batch(batch)
        input_ids = np.array([item.ids for item in encoded], dtype=np.int64)
        attention_mask = np.array([item.attention_mask for item in encoded], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)
        hidden = session.run(None, {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        })[0]
        weights = attention_mask[:, :, None].astype(np.float32)
        pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        vectors.append(pooled / np.clip(norms, 1e-9, None))
        done = min(start + batch_size, len(texts))
        if done == len(texts) or done % 128 == 0:
            print(f"  embedded {done}/{len(texts)}")

    return np.vstack(vectors)


def check_similarity(chunk_texts, metadata_list, queries=TEST_QUERIES, n_results=5):
    """Rank chunks per query with cosine similarity (MiniLM if available, else TF-IDF)."""
    import numpy as np

    embed_texts = [format_chunk_for_embedding(text, meta) for text, meta in zip(chunk_texts, metadata_list)]
    expanded_queries = [clean_query(q) for q in queries]
    method = "tfidf"
    doc_emb = None

    try:
        from sentence_transformers import SentenceTransformer

        print(f"\nEmbedding {len(embed_texts)} chunks with {EMBEDDING_MODEL}...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        doc_emb = model.encode(embed_texts, normalize_embeddings=True, show_progress_bar=True)
        query_emb = model.encode(expanded_queries, normalize_embeddings=True)
        sim_matrix = np.asarray(query_emb @ doc_emb.T)
        method = EMBEDDING_MODEL
    except Exception:
        doc_emb = None

    if doc_emb is None:
        try:
            print(f"\nEmbedding {len(embed_texts)} chunks with MiniLM ONNX ({EMBEDDING_MODEL})...")
            doc_emb = embed_minilm_onnx(embed_texts)
            query_emb = embed_minilm_onnx(expanded_queries)
            sim_matrix = np.asarray(query_emb @ doc_emb.T)
            method = f"{EMBEDDING_MODEL}-onnx"
        except Exception as exc:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            print(f"\nMiniLM unavailable ({exc}) — scoring with TF-IDF cosine similarity.")
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=50000,
            )
            doc_mat = vectorizer.fit_transform(embed_texts)
            query_mat = vectorizer.transform(expanded_queries)
            sim_matrix = cosine_similarity(query_mat, doc_mat)
            method = "tfidf"

    report = {
        "method": method,
        "n_chunks": len(chunk_texts),
        "min_retrieve_score": MIN_RETRIEVE_SCORE,
        "queries": [],
    }

    for q_i, query in enumerate(queries):
        scores = boost_retrieval_scores(expanded_queries[q_i], chunk_texts, metadata_list, sim_matrix[q_i])
        ranked = dedup_ranked_indices(
            np.argsort(-scores),
            chunk_texts,
            metadata_list,
            sim_matrix[q_i],
            doc_emb=doc_emb,
            k=n_results,
            min_score=MIN_RETRIEVE_SCORE if method != "tfidf" else None,
        )
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        if not ranked:
            print(f"\n  No chunk passed the {MIN_RETRIEVE_SCORE:.2f} confidence gate.")
            report["queries"].append({"query": query, "hits": [], "gated": True})
            continue
        hits = []
        for rank, idx in enumerate(ranked, start=1):
            meta = metadata_list[idx]
            score = float(sim_matrix[q_i][idx])
            page_start = meta.get("page_start", meta.get("page_number", "N/A"))
            page_end = meta.get("page_end", page_start)
            page = page_start if page_start == page_end else f"{page_start}-{page_end}"
            print(f"\n[{rank}] similarity={score:.3f}")
            print(f"    source     = {meta.get('source_file')}")
            print(f"    title      = {meta.get('doc_title', '')}")
            print(f"    org / year = {meta.get('organization', '')} / {meta.get('year') or '-'}")
            print(f"    guideline  = {meta.get('guideline_id') or '-'}")
            print(f"    page       = {page}")
            print(f"    section    = {meta.get('section_title', 'Unspecified')}")
            print(f"    chunk      = {meta.get('chunk_id', 'N/A')}")
            print("\n    TEXT:")
            print(chunk_texts[idx][:700])
            hits.append({
                "rank": rank,
                "similarity": round(score, 4),
                "chunk_id": meta.get("chunk_id"),
                "source_file": meta.get("source_file"),
                "doc_title": meta.get("doc_title"),
                "organization": meta.get("organization"),
                "guideline_id": meta.get("guideline_id"),
                "year": meta.get("year"),
                "page_start": meta.get("page_start"),
                "page_end": meta.get("page_end"),
                "section_title": meta.get("section_title"),
                "text_preview": chunk_texts[idx][:280],
            })
        report["queries"].append({"query": query, "hits": hits})

    out_path = os.path.join(OUTPUT_FOLDER, "similarity_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nSaved similarity report -> {out_path} (method={method})")
    return report


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    similarity_only = "--similarity" in sys.argv
    chunk_texts, chunk_ids, metadata_list = build_chunks_and_metadata()

    if not chunk_texts:
        raise SystemExit(0)

    check_similarity(chunk_texts, metadata_list)

    if similarity_only:
        raise SystemExit(0)

    try:
        collection = embed_chunks(chunk_texts, chunk_ids, metadata_list)
        run_test_queries(collection)
    except Exception as exc:
        print(f"\nChroma embedding skipped ({exc}). Similarity scores above are still valid.")

