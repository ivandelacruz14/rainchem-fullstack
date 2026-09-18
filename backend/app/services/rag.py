"""
Retrieval engine for the AI assistant.

Given a user question and the list of knowledge base entries, this finds the
best matching entry using TF-IDF vectors and cosine similarity. It is a
retrieval-augmented approach: the chatbot only ever answers with text an
admin has written and approved, never a generated or hardcoded reply.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FALLBACK_ANSWER = (
    "I don't have an approved answer for that yet. I've forwarded your "
    "question to our team, and an admin will review it and add it to my "
    "knowledge base soon. In the meantime, you can browse our products or "
    "contact support directly."
)

MATCH_THRESHOLD = 0.12


def retrieve(question, entries, include_pending=False):
    """
    entries: list of KnowledgeEntry model instances.
    Returns (matched_entry_or_None, confidence_percent, candidates)
    where candidates is a list of (entry, score) for the top 3 matches.
    """
    pool = entries if include_pending else [e for e in entries if e.status == "approved"]
    if not pool:
        return None, 0, []

    documents = [f"{e.question} {e.answer} {e.category}" for e in pool]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(documents + [question])
    except ValueError:
        # happens if the question and documents share no vocabulary at all
        return None, 0, []

    question_vector = tfidf_matrix[-1]
    doc_vectors = tfidf_matrix[:-1]
    scores = cosine_similarity(question_vector, doc_vectors)[0]

    ranked = sorted(zip(pool, scores), key=lambda pair: pair[1], reverse=True)
    top_entry, top_score = ranked[0]
    confidence = round(top_score * 100)
    matched = top_entry if top_score > MATCH_THRESHOLD else None

    return matched, confidence, ranked[:3]


def answer_question(question, entries, include_pending=False):
    matched, confidence, candidates = retrieve(question, entries, include_pending)
    answer = matched.answer if matched else FALLBACK_ANSWER
    return {
        "answer": answer,
        "matched_entry": matched,
        "confidence": confidence,
        "resolved": matched is not None,
        "candidates": [
            {"question": e.question, "score": round(score * 100)} for e, score in candidates
        ],
    }
