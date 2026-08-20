"""
STEP 1: EXTRACT TEXT FROM PDF
"""

import re
import pdfplumber


def find_column_split_x(page, min_gap_width=15, search_margin_frac=0.15):
    """
    Look for a genuine vertical whitespace gap near the middle of the page —
    a real sign of a two-column layout — by checking, across ALL words on
    the page, which x-ranges are ever covered by a word. A true column
    gap means that strip is empty for every line on the page, not just
    "few words happen to cross the exact midpoint" (that weaker check
    produces false positives on ordinary bulleted/short-line text, which
    then gets wrongly sliced down the middle, cutting words in half).
    Only gaps within the middle band of the page count (avoids mistaking
    normal margins for a column boundary). Returns the x-coordinate to
    split at, or None if no real column gap is found.
    """
    words = page.extract_words()
    if len(words) < 20:
        return None

    page_width = page.width
    resolution = 2  # points per bin
    n_bins = int(page_width // resolution) + 1
    covered = [False] * n_bins

    for w in words:
        start_bin = max(0, int(w["x0"] // resolution))
        end_bin = min(n_bins - 1, int(w["x1"] // resolution))
        for b in range(start_bin, end_bin + 1):
            covered[b] = True

    search_start = int(page_width * search_margin_frac)
    search_end = int(page_width * (1 - search_margin_frac))

    best_gap_start, best_gap_len = None, 0
    current_start, current_len = None, 0
    for x in range(search_start, search_end, resolution):
        b = x // resolution
        if b < n_bins and not covered[b]:
            if current_start is None:
                current_start = x
            current_len += resolution
        else:
            if current_len > best_gap_len:
                best_gap_start, best_gap_len = current_start, current_len
            current_start, current_len = None, 0
    if current_len > best_gap_len:
        best_gap_start, best_gap_len = current_start, current_len

    if best_gap_start is not None and best_gap_len >= min_gap_width:
        return best_gap_start + best_gap_len / 2

    return None


def extract_page_text(page):
    """
    Extract one page's text. If a genuine whitespace gap is found near the
    middle of the page (a real column boundary), split and read column by
    column so words from each column don't get interleaved into scrambled
    sentences. If no such gap exists, extract normally.
    """
    split_x = find_column_split_x(page)

    if split_x is not None:
        left = page.within_bbox((0, 0, split_x, page.height)).extract_text() or ""
        right = page.within_bbox((split_x, 0, page.width, page.height)).extract_text() or ""
        return (left + "\n" + right).strip()

    return page.extract_text() or ""


def detect_repeated_lines(page_texts, repeat_threshold=0.6, min_line_length=6):
    """
    Find lines that repeat across most pages of a document — running
    titles/headers, footer boilerplate — by normalizing digits (so page
    numbers don't prevent a match) and counting how many pages each line
    appears on.
    """
    if len(page_texts) < 3:
        return set()

    line_counts = {}
    for text in page_texts:
        lines_on_this_page = {
            re.sub(r"\d+", "#", line.strip().lower())
            for line in text.split("\n")
            if len(line.strip()) >= min_line_length
        }
        for norm_line in lines_on_this_page:
            line_counts[norm_line] = line_counts.get(norm_line, 0) + 1

    n_pages = len(page_texts)
    return {line for line, count in line_counts.items() if count / n_pages >= repeat_threshold}


def strip_repeated_lines(text, repeated_lines):
    kept = []
    for line in text.split("\n"):
        norm_line = re.sub(r"\d+", "#", line.strip().lower())
        if norm_line in repeated_lines and line.strip():
            continue
        kept.append(line)
    return "\n".join(kept)


def extract_text_from_pdf(pdf_path):
    """
    Read a PDF and return a list of (page_number, page_text) tuples —
    one entry per page, page_number starting at 1. Also strips lines that
    repeat across most pages of THIS document (running titles/footers).
    """
    raw_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = extract_page_text(page)
            raw_pages.append((i + 1, page_text))

    page_texts_only = [text for _, text in raw_pages]
    repeated_lines = detect_repeated_lines(page_texts_only)

    if repeated_lines:
        raw_pages = [
            (page_num, strip_repeated_lines(text, repeated_lines))
            for page_num, text in raw_pages
        ]

    return raw_pages
