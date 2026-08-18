"""
STEP 10a: GENERATION — answer the query from the retrieved, cited chunks.

Uses the `client` object you already set up in config.py (reading its
API key from .env) — this module doesn't touch API keys directly at all.
"""

from settings import GENERATION_MODEL, GENERATION_SYSTEM_PROMPT
from citations import build_context_with_citations
from config import client


def generate_answer(query, results, model=GENERATION_MODEL):
    """
    Calls the LLM (via the client configured in config.py) with the
    retrieved+cited context and returns its generated answer text.
    """
    if not results:
        return "No relevant information was found in the corpus for this query."

    context_block = build_context_with_citations(results)

    user_prompt = (
        f"Context passages:\n\n{context_block}\n\n"
        f"Question: {query}\n\n"
        f"Answer the question using only the passages above, with [n] citations."
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
