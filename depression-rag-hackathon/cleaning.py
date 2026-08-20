"""
STEP 2: CLEAN TEXT
"""

import re


def clean_text(text):
    """
    Basic cleanup so noisy PDF text doesn't mislead the RAG system:
      - remove URLs and emails
      - remove citation markers like [12] or (Smith et al., 2020)
      - remove copyright notices and "Published/Last updated" boilerplate
      - remove standalone page numbers
      - fix hyphenated line breaks ("depres-\\nsion" -> "depression")
      - collapse extra whitespace
    """
    # fix words broken across lines by a hyphen
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # remove URLs and emails
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\S+@\S+\.\S+", "", text)

    # remove citation markers, e.g. [12]  or (Smith et al., 2020)
    text = re.sub(r"\[\s*\d+(\s*[-,]\s*\d+)*\s*\]", "", text)
    text = re.sub(r"\([A-Z][a-zA-Z]+(\s+et al\.?)?,?\s*\d{4}\)", "", text)

    # remove copyright notices, e.g. "© NICE 2026"
    text = re.sub(r"©\s*[A-Za-z][A-Za-z .]{0,30}\d{4}\.?", "", text)
    text = re.sub(r"all rights reserved\.?", "", text, flags=re.IGNORECASE)

    # remove "Published: <date>" / "Last updated: <date>" boilerplate
    text = re.sub(r"\b(Published|Last updated)\s*:\s*\d{1,2}\s+\w+\s+\d{4}", "", text, flags=re.IGNORECASE)

    # remove NICE-style "Subject to Notice of rights (...). 111" footer,
    # plus the trailing "Page X of Y" fragment it's often glued to
    text = re.sub(r"Subject to Notice of rights\s*\([^)]*\)\.?\s*\d*\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPage\s+\d+\s+of\s+\d+\b\.?", "", text, flags=re.IGNORECASE)

    # remove lines that are just a page number
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)

    # collapse repeated whitespace/newlines
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
