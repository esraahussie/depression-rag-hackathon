import streamlit as st
import json
import chromadb
from chromadb.utils import embedding_functions

from day3_generation import generate_answer as generate_grounded_answer

OUTPUT_FOLDER = "outputs"
CHROMA_FOLDER = f"{OUTPUT_FOLDER}/chroma_db"
COLLECTION_NAME = "depression_clinical"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Day 3 calibrated thresholds
CALIBRATION_FILE = f"{OUTPUT_FOLDER}/day3_calibration.json"

DEFAULT_RETRIEVE_GATE = 0.53
DEFAULT_MEDIUM_CUTOFF = 0.53
DEFAULT_HIGH_CUTOFF = 0.68

def load_calibrated_thresholds():
    """Load thresholds produced by: python day3_generation.py --calibrate"""
    thresholds = {
        "retrieval_gate": DEFAULT_RETRIEVE_GATE,
        "medium_cutoff": DEFAULT_MEDIUM_CUTOFF,
        "high_cutoff": DEFAULT_HIGH_CUTOFF,
    }
    try:
        with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
            calibration = json.load(f)
        thresholds["retrieval_gate"] = float(calibration.get("retrieval_gate", thresholds["retrieval_gate"]))
        thresholds["medium_cutoff"] = float(calibration.get("medium_cutoff", thresholds["medium_cutoff"]))
        thresholds["high_cutoff"] = float(calibration.get("high_cutoff", thresholds["high_cutoff"]))
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return thresholds

CALIBRATED = load_calibrated_thresholds()
MIN_RETRIEVE_SCORE = CALIBRATED["retrieval_gate"]
MEDIUM_CONFIDENCE_THRESHOLD = CALIBRATED["medium_cutoff"]
HIGH_CONFIDENCE_THRESHOLD = CALIBRATED["high_cutoff"]

EXAMPLE_QUERIES = [
    "Should adults be screened for depression?",
    "What treatments are recommended for depression?",
    "How is depression severity assessed?",
]

st.set_page_config(page_title="Depression Guideline Evidence Search", page_icon="🩺", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(180deg, #eef2ff 0%, #e0e7ff 100%);
    background-attachment: fixed;
}

#MainMenu, footer, header { visibility: hidden; }

.hero {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #3b82f6 100%);
    border-radius: 18px;
    padding: 2.4rem 2.6rem;
    margin-bottom: 1.6rem;
    color: white;
    box-shadow: 0 10px 30px rgba(37, 99, 235, 0.25);
}
.hero h1 {
    font-size: 2rem;
    font-weight: 800;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.02em;
}
.hero p {
    font-size: 1rem;
    opacity: 0.92;
    margin: 0;
    max-width: 640px;
    line-height: 1.5;
}
.stat-row { display: flex; gap: 0.8rem; margin-top: 1.4rem; flex-wrap: wrap; }
.stat-chip {
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.22);
    border-radius: 999px;
    padding: 6px 16px;
    font-size: 0.82rem;
    font-weight: 600;
    backdrop-filter: blur(4px);
}

.section-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    margin: 0.4rem 0 0.7rem 2px;
}

div[data-testid="stTextInput"] input {
    border-radius: 12px;
    border: 1.5px solid #e2e8f0;
    padding: 0.7rem 1rem;
    font-size: 0.98rem;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

.stButton>button {
    border-radius: 10px;
    font-weight: 600;
    border: 1.5px solid #e2e8f0;
    background: white;
    color: #374151;
    transition: all 0.15s ease;
}
.stButton>button:hover {
    border-color: #3b82f6;
    color: #2563eb;
    transform: translateY(-1px);
}
button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1e40af) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
}
button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(37,99,235,0.4);
}

.evidence-card {
    background: white;
    border-radius: 14px;
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.evidence-card:hover {
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}
.rank-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: #eff6ff;
    color: #1d4ed8;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 8px;
}
.confidence-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 700;
    margin-right: 8px;
    letter-spacing: 0.01em;
}
.confidence-high { background: #dcfce7; color: #15803d; }
.confidence-medium { background: #fef3c7; color: #a16207; }
.confidence-low { background: #fee2e2; color: #b91c1c; }
.similarity-tag {
    color: #9ca3af;
    font-size: 0.78rem;
    font-weight: 500;
}
.citation-line {
    color: #6b7280;
    font-size: 0.84rem;
    margin: 8px 0 12px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid #f1f5f9;
}
.citation-line b { color: #374151; }
.chunk-text {
    color: #1f2937;
    line-height: 1.65;
    font-size: 0.95rem;
}

.disclaimer-box {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 0.9rem 1.1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    color: #1e3a5f;
    line-height: 1.5;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #dbe4ff 0%, #c7d2fe 100%);
    border-right: 1px solid #a5b4fc;
}
section[data-testid="stSidebar"] * {
    color: #1e2a5e;
}

[data-testid="stAlert"] {
    background-color: #fff7d6 !important;
    border: 1px solid #f0c36d !important;
}

[data-testid="stAlert"] * {
    color: #6b4f00 !important;
}

[data-testid="stExpander"] * {
    color: #1e2a5e !important;
}

/* Chat answer text */
div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    color: #1f2937 !important;
}

div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
    color: #1f2937 !important;
}

div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
    color: #1f2937 !important;
}

div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong {
    color: #111827 !important;
}

div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em {
    color: #4b5563 !important;
}

div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 {
    color: #111827 !important;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_collection():
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )


def confidence_from_similarity(similarity):
    """Map retrieval similarity to the calibrated confidence level."""
    if similarity < MIN_RETRIEVE_SCORE:
        return "Insufficient Evidence", "confidence-low"
    if similarity >= HIGH_CONFIDENCE_THRESHOLD:
        return "High confidence", "confidence-high"
    if similarity >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "Medium confidence", "confidence-medium"
    return "Low confidence", "confidence-low"


def format_page_range(meta):
    start = meta.get("page_start") or meta.get("page_number")
    end = meta.get("page_end") or start
    if not start:
        return "N/A"
    return str(start) if start == end else f"{start}\u2013{end}"


def format_citation_html(meta):
    organization = meta.get("organization") or ""
    guideline_id = meta.get("guideline_id") or ""
    doc_title = meta.get("doc_title") or meta.get("source_file", "unknown")
    section = meta.get("section_title") or "Unspecified"
    year = meta.get("year") or ""
    source_url = meta.get("source_url") or ""
    page_range = format_page_range(meta)

    org_line = " · ".join(x for x in [organization, guideline_id, str(year) if year else ""] if x)
    org_html = f" · {org_line}" if org_line else ""
    link_html = f'<br><a href="{source_url}" target="_blank">{source_url}</a>' if source_url else ""

    return (
        f'<div class="citation-line">'
        f'<b>{doc_title}</b>{org_html}<br>'
        f'Page {page_range} · Section: {section}'
        f'{link_html}'
        f'</div>'
    )


def run_search(collection, query, n_results, source_filter):
    where_clause = {"source_file": {"$in": source_filter}} if source_filter else None
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_clause,
    )
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    return list(zip(documents, metadatas, distances))


collection = load_collection()
total_chunks = collection.count()

st.markdown(f"""
<div class="hero">
    <h1>🩺 Depression Guideline Evidence Search</h1>
    <p>Retrieval-only evidence panel, grounded strictly in official clinical guideline documents.
    Every result traces back to a source, page, and passage — no generation layer, no hallucinated claims.</p>
    <div class="stat-row">
        <div class="stat-chip">📄 {total_chunks} chunks indexed</div>
    </div>
</div>
""", unsafe_allow_html=True)

CONFIDENCE_BADGE_CLASS = {
    "High": "confidence-high",
    "Medium": "confidence-medium",
    "Low": "confidence-low",
    "Insufficient Evidence": "confidence-low",
}


def render_structured_answer(answer):
    """Render the Step 2 answer schema (recommendation, supporting_evidence,
    citations, confidence, disclaimer) from day3_generation.generate_answer()
    as markdown for st.chat_message. Every claim shown here is traceable to
    the citations block below it (Day 3, Step 3/4)."""
    confidence = answer.get("confidence") or "Insufficient Evidence"
    badge_class = CONFIDENCE_BADGE_CLASS.get(confidence, "confidence-low")
    method = answer.get("_generation_method", "unknown")
    method_label = "LLM-generated" if method == "llm" else "Extractive fallback (no LLM key set)"

    lines = [
        f'<span class="confidence-badge {badge_class}">{confidence}</span> '
        f'<span class="similarity-tag">{method_label} · {answer.get("n_hits", 0)} chunks retrieved</span>',
        "",
    ]

    recommendation = answer.get("recommendation")
    if recommendation:
        lines.append(recommendation)
    else:
        lines.append(
            "_The retrieved guidelines do not provide sufficient evidence to answer "
            "this question reliably. Please consult the relevant clinical guideline "
            "or a qualified clinician._"
        )

    citations = answer.get("citations") or []
    if citations:
        lines.append("\n**Citations**")
        for c in citations:
            doc = c.get("document_name") or "Unknown source"
            section = c.get("section_title") or "Unspecified"
            page = c.get("page") or "N/A"
            score = c.get("retrieval_score")
            score_str = f" · score {score:.2f}" if isinstance(score, (int, float)) else ""
            lines.append(f"- {doc} — *{section}*, p.{page}{score_str}")

    disclaimer = answer.get("disclaimer") or (
        "This is guideline-derived support information, not a substitute for clinical judgment."
    )
    lines.append(f"\n*{disclaimer}*")

    return "\n".join(lines)


if total_chunks == 0:
    st.warning("No chunks are indexed yet. Run the ingestion pipeline to populate the vector store before searching.")
    st.stop()

all_metadata_sample = collection.get(limit=total_chunks, include=["metadatas"])["metadatas"]
all_sources = sorted(set(m.get("source_file", "unknown") for m in all_metadata_sample))

with st.sidebar:
    st.markdown("### ⚙️ Filters")
    source_filter = st.multiselect("Source document", all_sources, default=all_sources)
    n_results = st.slider("Number of results", min_value=3, max_value=15, value=5)

    st.markdown("### 📊 Calibrated thresholds")
    st.caption(
        f"Retrieval gate: **{MIN_RETRIEVE_SCORE:.3f}**  \n"
        f"Medium cutoff: **{MEDIUM_CONFIDENCE_THRESHOLD:.3f}**  \n"
        f"High cutoff: **{HIGH_CONFIDENCE_THRESHOLD:.3f}**"
    )

tab_search, tab_chat = st.tabs(["🔍 Evidence Search", "💬 Chat"])

with tab_search:
    st.markdown('<div class="section-label">Ask a question</div>', unsafe_allow_html=True)

    cols = st.columns(len(EXAMPLE_QUERIES))
    example_clicked = None
    for col, example in zip(cols, EXAMPLE_QUERIES):
        if col.button(example, use_container_width=True, key=f"example_{example}"):
            example_clicked = example

    input_col, button_col = st.columns([5, 1])
    with input_col:
        query = st.text_input(
            "Question",
            value=example_clicked if example_clicked else "",
            placeholder="e.g. Should adults be screened for depression?",
            label_visibility="collapsed",
        )
    with button_col:
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    if (search_clicked or example_clicked) and query.strip():
        with st.spinner("Retrieving evidence..."):
            results = run_search(collection, query, n_results, source_filter)

        if not results:
            st.info(
                "No relevant evidence found for this query. "
                "This may be out of scope for the indexed guidelines."
            )
        else:
            # Step 5: apply the retrieval gate before showing evidence to the user.
            # Results below the gate are kept only for optional debugging.
            accepted_results = []
            rejected_results = []

            for rank, (text, meta, distance) in enumerate(results, start=1):
                similarity = 1 - distance

                if similarity >= MIN_RETRIEVE_SCORE:
                    accepted_results.append(
                        (rank, text, meta, distance, similarity)
                    )
                else:
                    rejected_results.append(
                        (rank, text, meta, distance, similarity)
                    )

            if not accepted_results:
                # User-facing result: do not expose irrelevant low-scoring chunks.
                st.warning(
                    "No sufficiently relevant evidence was found in the "
                    "available depression guidelines."
                )

                st.caption(
                    f"All {len(results)} retrieved results were below the "
                    f"retrieval gate of {MIN_RETRIEVE_SCORE:.2f}."
                )

            else:
                st.markdown(
                    f'<div class="section-label">Evidence · '
                    f'{len(accepted_results)} results</div>',
                    unsafe_allow_html=True,
                )

                for rank, text, meta, distance, similarity in accepted_results:
                    label, badge_class = confidence_from_similarity(similarity)

                    card_html = (
                        f'<div class="evidence-card">'
                        f'<span class="rank-badge">{rank}</span>'
                        f'<span class="confidence-badge {badge_class}">{label}</span>'
                        f'<span class="similarity-tag">similarity {similarity:.2f}</span>'
                        f'{format_citation_html(meta)}'
                        f'<div class="chunk-text">{text}</div>'
                        f'</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)

            # Optional developer/debug view for evidence rejected by the gate.
            if rejected_results:
                with st.expander(
                    f"🔧 Debug / retrieval details · "
                    f"{len(rejected_results)} result(s) below gate"
                ):
                    st.caption(
                        "These chunks were retrieved by ChromaDB but are hidden "
                        "from the user because their similarity is below the "
                        f"retrieval gate ({MIN_RETRIEVE_SCORE:.2f})."
                    )

                    for rank, text, meta, distance, similarity in rejected_results:
                        label, badge_class = confidence_from_similarity(similarity)

                        st.markdown(
                            f"**#{rank} · {label} · similarity {similarity:.2f}**"
                        )
                        st.markdown(format_citation_html(meta), unsafe_allow_html=True)
                        st.caption(text)
                        st.divider()

with tab_chat:
    st.info(
        "Answers are generated only from retrieved guideline chunks (Groq LLM if "
        "`GROQ_API_KEY` is set, otherwise an extractive fallback). Every claim below "
        "should be traceable to the citations listed under it."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    user_message = st.chat_input("Ask a question about the indexed guidelines...")

    if user_message:
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving evidence and generating a grounded answer..."):
                # NOTE: generate_grounded_answer() does its own retrieval via
                # day3_generation.retrieve_context() (same Chroma collection,
                # same MIN_RETRIEVE_SCORE gate). The source_filter multiselect
                # in the sidebar only applies to the Evidence Search tab for now.
                answer = generate_grounded_answer(user_message, k=n_results)
            rendered = render_structured_answer(answer)
            st.markdown(rendered, unsafe_allow_html=True)

        st.session_state.chat_history.append({"role": "assistant", "content": rendered})

st.markdown("""
<div class="disclaimer-box">
⚕️ This tool supports — never replaces — clinical judgment. Outputs are guideline-grounded evidence excerpts,
not diagnostic or treatment recommendations.
</div>
""", unsafe_allow_html=True)
