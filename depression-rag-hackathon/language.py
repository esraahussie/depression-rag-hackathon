"""
Egyptian Arabic interface support.

Retrieval stays on English guideline chunks. Arabic questions are translated
to English before search; answers are written in Egyptian Arabic with [n] citations.
"""

import re

from config import client
from settings import GENERATION_MODEL

ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06FF]")

OUT_OF_SCOPE_AR = (
    "السؤال ده برة شغل مايند كير. أقدر أساعد في الصحة النفسية "
    "اللي موجودة في الإرشادات الطبية اللي عندنا بس."
)

INSUFFICIENT_EVIDENCE_AR = (
    "سؤالك قريب من الصحة النفسية، بس الأوراق اللي عندنا مش مكفية "
    "عشان أجاوبك صح. جرّب تصيغه بطريقة تانية، أو كلّم دكتور."
)

GENERATION_SYSTEM_PROMPT_ARZ = (
    "أنت مساعد طبي في تطبيق مايند كير. اتكلم مصري عامي قاهري "
    "زي ما الدكتور بيشرح للمريض في العيادة في مصر — مش فصحى، مش خليجي، مش شامي.\n"
    "استخدم كلام الناس في مصر: إيه، ده/دي، اللي، عشان، مش، مفيش، دلوقتي، "
    "كده، يعني، عندك، هتحس، ممكن، لازم، شوية، أوي.\n"
    "متستخدمش فصحى زي: الذي، التي، يجب على المريض، ينبغي، حيث إن، فإن، كما أن، يعتبر، يتم.\n"
    "القواعد:\n"
    "1. كل معلومة تخلّص بـ [n] من أرقام المصادر المعطاة.\n"
    "2. استخدم أرقام المصدر الموجودة في الفهرس فقط — متختراعش أرقام جديدة.\n"
    "3. لو الفقرات مش كافية، قول كده بصراحة. متخمّنش.\n"
    "4. متستخدمش معلومات من برة المصادر. متنفعش أسئلة برة الموضوع.\n"
    "5. أسماء الأدوية والإرشادات (NICE, WHO, PHQ-9) تفضل بالإنجليزي.\n"
    "6. علامات الاستشهاد [n] تفضل أرقام لاتينية زي [1] و[2].\n"
    "7. متستخدمش ماركداون خالص: لا ** ولا * ولا # ولا قوائم بنجوم. اكتب جمل عادية."
)


def contains_arabic(text: str) -> bool:
    return bool(ARABIC_CHAR_RE.search(text or ""))


def resolve_language(query: str, requested: str | None = None) -> str:
    """
    requested: 'en' | 'arz' | 'auto' | None
    Arabic script always wins. Otherwise honor the UI language toggle.
    """
    if contains_arabic(query):
        return "arz"
    choice = (requested or "auto").strip().lower()
    if choice in {"arz", "ar", "arabic", "egyptian"}:
        return "arz"
    return "en"


def translate_to_english(text: str) -> str:
    """Translate Egyptian/MSA Arabic to an English retrieval query. English is unchanged."""
    if not text or not contains_arabic(text):
        return text
    if client is None:
        return text
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            max_tokens=300,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the user's question from Egyptian Arabic or Modern Standard "
                        "Arabic into clear clinical English. Output ONLY the English question. "
                        "Keep drug names, guideline IDs, and abbreviations (PHQ-9, SSRI, NICE)."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        translated = (response.choices[0].message.content or "").strip()
        return translated or text
    except Exception:
        return text


def localize_extractive_answer(english_answer: str) -> str:
    """Best-effort Egyptian Arabic rendering of an extractive English fallback."""
    if not english_answer or client is None:
        return english_answer
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            max_tokens=1000,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "حوّل الرد لمصري عامي قاهري زي كلام العيادة في مصر، مش فصحى. "
                        "استخدم إيه/ده/اللي/عشان/مش/دلوقتي. متستخدمش الذي/التي/يجب. "
                        "سيّب كل علامة [n] زي ما هي. متزودش معلومات طبية. "
                        "أسماء الأدوية والإرشادات بالإنجليزي. "
                        "متستخدمش نجوم ** ولا ماركداون."
                    ),
                },
                {"role": "user", "content": english_answer},
            ],
        )
        rewritten = (response.choices[0].message.content or "").strip()
        return rewritten or english_answer
    except Exception:
        return english_answer
