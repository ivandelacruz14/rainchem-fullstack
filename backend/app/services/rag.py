"""
Retrieval engine for the Rainchem AI assistant.

Given a customer question, this finds the best answer from two trusted
sources and never invents text:

  1. Admin-approved knowledge base entries (FAQ style answers).
  2. The live product catalog (price, stock, specs), so questions like
     "magkano ang RadCool?" are answered from real, current data.

Why the old version answered the wrong thing, and what changed:

  * It fitted TF-IDF on the documents *plus the question*, so the question
    polluted its own IDF weights. Now the index is built from the documents
    only, and is cached.
  * It matched the question against question + answer + category mashed into
    one blob, so a long answer mentioning "oil" could beat the entry that was
    actually about the user's question. Now question and answer text are
    scored separately, with the stored question weighted higher.
  * It used English stop words and no stemming, so Tagalog / Taglish
    ("magkano", "palit langis", "gaano katagal") matched nothing, and
    "changing" never matched "change". Now questions are normalized: Taglish
    terms are mapped to the English vocabulary used in the knowledge base and
    words are stemmed.
  * Pure cosine similarity rewards short documents. A "coverage" score now
    checks how much of what the user asked is actually present in the entry.
  * Character n-grams make it tolerant to typos ("colant", "rad cool").
  * A single low threshold made it answer confidently with the wrong entry.
    Now there are three outcomes: confident answer, "did you mean...?"
    suggestions when it is unsure, and an honest fallback.
"""

import hashlib
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Tunable settings
# Score (0-1) needed to answer directly from the knowledge base.
KB_ANSWER_MIN = 0.34
# Score needed to offer entries as "did you mean...?" suggestions.
SUGGEST_MIN = 0.16
# Score needed for a product to be used as the answer.
PRODUCT_MIN = 0.30
# Products within this fraction of the best product score are listed together.
PRODUCT_GROUP_RATIO = 0.80
# Very short questions ("coolant", "oil") with several equally good matches
# get a "which one do you mean?" reply instead of a random pick.
CLARIFY_MAX_TOKENS = 3
CLARIFY_MARGIN = 0.12

FALLBACK_ANSWER = (
    "I don't have an approved answer for that yet. I've saved your question "
    "so our team can review it and add it to my knowledge base. In the "
    "meantime, you can browse our products or contact support directly."
)
FALLBACK_ANSWER_TL = (
    "Pasensya na, wala pa akong naka-approve na sagot para diyan. Na-save ko "
    "na ang tanong mo para ma-review ng team namin at maidagdag sa knowledge "
    "base ko. Pansamantala, puwede kang mag-browse ng mga produkto o "
    "makipag-ugnayan sa support."
)
FALLBACK_WITH_SUGGESTIONS = (
    "I'm not fully sure I understood that. Did you mean one of these? "
    "If not, I've saved your question so our team can review it."
)
FALLBACK_WITH_SUGGESTIONS_TL = (
    "Hindi ako sigurado kung naintindihan ko nang tama. Ito ba ang ibig mong "
    "sabihin? Kung hindi, na-save ko na ang tanong mo para ma-review ng team."
)
CLARIFY_ANSWER = "I can help with a few things about that. Which one do you mean?"
CLARIFY_ANSWER_TL = "May ilang puwede akong ipaliwanag tungkol diyan. Alin ang ibig mong sabihin?"
REPHRASE_ANSWER = (
    "Could you tell me a bit more? Try asking about our products, prices, "
    "delivery, payment, or how to take care of your motorcycle."
)
# Text normalization (English + Tagalog / Taglish)
# Multi-word phrases rewritten before tokenizing.
_PHRASES = [
    (r"(\d+w)\s*[-/ ]?\s*(\d+)", r"\1\2"),             # 10w-40 -> 10w40
    (r"\brad\s+cool\b", " radcool "),
    (r"\bhow\s+much\b", " price "),
    (r"\bhow\s+often\b", " often "),
    (r"\bhow\s+long\b", " long "),
    (r"\bgaano\s+katagal\b", " long "),
    (r"\bgaano\s+ka\s*dalas\b", " often "),
    (r"\bshelf\s+life\b", " expire "),
    (r"\b(engine|motor|motorcycle)\s+oil\b", " oil "),
    (r"\bradiator\s+(fluid|coolant|water)\b", " coolant "),
    (r"\btubig\s+(ng\s+)?radiator\b", " coolant "),
    (r"\bcash\s+on\s+delivery\b", " payment "),
    (r"\b(log\s*in|sign\s*in|sign\s*up|register)\b", " login "),
    (r"\bout\s+of\s+stock\b", " stock "),
    (r"\bin\s+stock\b", " stock "),
    (r"\bcustomer\s+(service|support|care)\b", " contact "),
]

# Single-token synonyms: Taglish / variants -> the English word that the
# knowledge base (and product catalog) actually uses.
_SYNONYMS = {
    # oil & maintenance
    "langis": "oil", "oyl": "oil", "lubricant": "oil",
    "sintetiko": "synthetic", "synth": "synthetic",
    "kilometro": "km", "kilometer": "km", "kilometers": "km", "kilometre": "km", "kms": "km",
    "kadalas": "often", "madalas": "often",
    "tagal": "long", "katagal": "long", "tumagal": "long", "magtagal": "long",
    "motor": "motorcycle", "motorsiklo": "motorcycle", "motorbike": "motorcycle", "bike": "motorcycle",
    "makina": "engine",
    "kadena": "chain", "salaan": "filter",
    # coolant
    "antifreeze": "coolant", "kulant": "coolant", "colant": "coolant", "coolent": "coolant",
    "dilute": "mix", "diluted": "mix", "dilution": "mix", "ihalo": "mix", "haluan": "mix",
    "paghaluin": "mix", "halo": "mix", "pagsamahin": "mix", "isama": "mix",
    # price / buying
    "magkano": "price", "presyo": "price", "halaga": "price", "cost": "price", "costs": "price",
    "pricing": "price", "prices": "price", "php": "price", "peso": "price", "pesos": "price",
    "bili": "buy", "bumili": "buy", "bilhin": "buy", "purchase": "buy", "bibili": "buy",
    "diskwento": "discount", "tawad": "discount", "promo": "discount", "sale": "discount",
    "bulk": "discount", "wholesale": "discount", "tingi": "retail",
    # stock
    "available": "stock", "availability": "stock", "avail": "stock", "restock": "stock",
    # delivery & orders
    "delivery": "deliver", "delivered": "deliver", "deliveries": "deliver", "delivering": "deliver",
    "shipping": "deliver", "ship": "deliver", "shipped": "deliver", "shipment": "deliver",
    "courier": "deliver", "padala": "deliver", "ipadala": "deliver", "hatid": "deliver",
    "ihatid": "deliver", "dumating": "deliver", "darating": "deliver", "dadating": "deliver",
    "tracking": "track", "subaybayan": "track", "trace": "track",
    "umorder": "order", "magorder": "order", "iorder": "order", "orders": "order",
    "kanselahin": "cancel", "ikansela": "cancel", "kansela": "cancel", "cancellation": "cancel",
    "ibalik": "return", "refund": "return", "returns": "return", "palitan": "change",
    "replace": "change", "replacing": "change", "replacement": "change", "replaced": "change",
    "swap": "change", "renew": "change",
    # payment
    "bayad": "payment", "bayaran": "payment", "magbayad": "payment", "ibayad": "payment",
    "pay": "payment", "paying": "payment", "gcash": "payment", "cod": "payment",
    "card": "payment", "cards": "payment", "credit": "payment", "debit": "payment",
    # services
    "serbisyo": "service", "services": "service", "install": "installation",
    "ikabit": "installation", "ipakabit": "installation", "kabit": "installation",
    "installing": "installation", "installed": "installation",
    "linis": "clean",
    # misc
    "garantiya": "warranty", "guarantee": "warranty",
    "expired": "expire", "expiry": "expire", "expiration": "expire", "expires": "expire",
    "tirahan": "address", "contacts": "contact", "tawagan": "contact", "support": "contact",
    "ebike": "motorcycle",
}

# Roots that identify a Tagalog verb/noun regardless of affixes
# (magpalit, papalitan, pagpapalit, nagpalit ...). Only roots of 4+ letters.
_TAGALOG_ROOTS = [
    ("palit", "change"),
    ("langis", "oil"),
    ("bayad", "payment"),
    ("padala", "deliver"),
    ("hatid", "deliver"),
    ("haluin", "mix"),
    ("halu", "mix"),
    ("presyo", "price"),
    ("kabit", "installation"),
]

_STOPWORDS = set("""
a an the and or but if of to in on at by for with from as is are was were be been being am do does did done doing
have has had having i me my mine we our us you your yours he she it its they them their this that these those there
here can could will would shall should may might must not no yes also just very so than then too any some all each
both more most other such only own same what which who whom whose when where why how about into over under again
further once up down out off please pls hi hello hey kindly want need like get got let know tell ask question
wondering much many one use help gusto gustong nais itanong take takes taking took go goes going
ang ng nang mga sa na ba bang po ko mo ako ka ay at o kung para yung yun ung ito iyon iyan yan naman lang din rin
ni si kay kayo ikaw kami namin natin nila nyo niyo ninyo pa pala opo oo ano anong ilan ilang paano pano gaano saan
sino kailan kelan bakit may mayroon meron pwede puwede maaari kaya daw raw ho sana talaga lamang muna kasi dahil
kapag pag tapos tsaka saka itong nito dito doon diyan nasa mula hanggang upang sila kanila amin atin aking iyong
kanyang alin magtanong tanong salamat
thanks thank thankyou ty bye goodbye paalam ingat later see ok okay oks sige maraming
good morning afternoon evening magandang umaga hapon gabi kumusta musta kamusta hola yo
""".split())

# Words that show the user wrote in Tagalog / Taglish (used to pick the
# language of the fallback reply).
_TAGALOG_MARKERS = {
    "ang", "ng", "mga", "ba", "po", "ko", "mo", "paano", "pano", "magkano", "gaano", "saan", "ano", "anong",
    "pwede", "puwede", "yung", "ung", "kailan", "kelan", "meron", "mayroon", "langis", "palit", "bayad",
    "padala", "hatid", "presyo", "naman", "lang", "kasi", "bakit", "ilang", "namin", "natin", "sa", "na",
}

_GREETINGS = {"hi", "hello", "hey", "hola", "kumusta", "musta", "kamusta", "good", "morning", "afternoon", "evening",
              "po", "there", "ka", "kayo", "yo", "magandang", "umaga", "hapon", "gabi"}
_THANKS = {"thanks", "thank", "thankyou", "ty", "salamat", "maraming", "po", "you", "so", "much", "very"}
_BYE = {"bye", "goodbye", "paalam", "ingat", "see", "later"}

# "Topic" words: if the user asks about one of these and the matched entry never
# mentions it, the entry is probably answering a different question (e.g. asking
# whether RadCool *expires* must not return the entry about *mixing* RadCool).
_TOPIC_WORDS = {
    "expire", "warranty", "return", "cancel", "discount", "price", "stock", "deliver",
    "payment", "track", "installation", "retail", "login", "contact",
}
# Weight (vs. the rarest known word) of query words absent from the whole index.
UNKNOWN_WORD_WEIGHT = 0.5
# ...and numbers / model codes (125, nmax155) count even less.
UNKNOWN_NUMBER_WEIGHT = 0.1
# Missing one of these topics costs this much of the score, per missed topic.
MISSED_TOPIC_PENALTY = 0.5

_PRICE_WORDS = {"price"}
_STOCK_WORDS = {"stock", "meron", "mayroon"}
_SPEC_WORDS = {"spec", "specs", "specification", "specifications", "viscosity", "volume", "liter", "litre",
               "size", "fit", "fits", "compatible", "compatibility", "jaso", "api", "grade", "ingredients"}
_USAGE_WORDS = {"usage", "instructions", "apply"}


def _stem(word):
    """Very small suffix stripper so oils/oil, changing/change, mixed/mix match."""
    if len(word) <= 3 or word.isdigit():
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("ing") and len(word) > 5:
        word = word[:-3]
    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("es") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        word = word[:-1]
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


_TOPIC_STEMS = None


def _topic_stems():
    global _TOPIC_STEMS
    if _TOPIC_STEMS is None:
        _TOPIC_STEMS = {_stem(t) for t in _TOPIC_WORDS}
    return _TOPIC_STEMS


def _canonical(token):
    """Map one raw token to its canonical English form (before stemming)."""
    if token in _SYNONYMS:
        return _SYNONYMS[token]
    for root, canon in _TAGALOG_ROOTS:
        if root in token:
            return canon
    return token


def _raw_tokens(text):
    text = (text or "").lower()
    for pattern, repl in _PHRASES:
        text = re.sub(pattern, repl, text)
    text = re.sub(r"[^a-z0-9\u00f1]+", " ", text)
    return [t for t in text.split() if t]


def _analyze(text):
    """
    Returns (normalized_text, content_tokens, intents, raw_tokens).
    normalized_text is what gets indexed / compared.
    """
    raw = _raw_tokens(text)
    mapped = [_canonical(t) for t in raw]
    intents = set()
    if any(t in _PRICE_WORDS for t in mapped):
        intents.add("price")
    if any(t in _STOCK_WORDS for t in mapped) or any(t in _STOCK_WORDS for t in raw):
        intents.add("stock")
    if any(t in _SPEC_WORDS for t in mapped):
        intents.add("specs")
    if any(t in _USAGE_WORDS for t in mapped):
        intents.add("usage")
    content = [_stem(t) for t in mapped if t not in _STOPWORDS and len(t) > 1]
    return " ".join(content), content, intents, raw


def _looks_tagalog(raw_tokens):
    hits = sum(1 for t in raw_tokens if t in _TAGALOG_MARKERS)
    return hits >= 2 or any(t in {"magkano", "paano", "pano", "gaano", "meron", "mayroon"} for t in raw_tokens)

# Index

class _Doc:
    """A searchable item. primary = title/question, body = details, tag = category."""

    __slots__ = ("ref", "primary", "body", "tag")

    def __init__(self, ref, primary, body, tag=""):
        self.ref = ref
        self.primary = primary or ""
        self.body = body or ""
        self.tag = tag or ""


class _Index:
    def __init__(self, docs):
        self.docs = docs
        primary = [_analyze(d.primary)[0] for d in docs]
        body = [_analyze(d.body)[0] for d in docs]
        tag = [_analyze(d.tag)[0] for d in docs]
        full = [f"{p} {b} {t}".strip() for p, b, t in zip(primary, body, tag)]

        self.token_sets = [set(f.split()) for f in full]
        self.primary_sets = [set(f"{p} {t}".split()) for p, t in zip(primary, tag)]

        self.word = TfidfVectorizer(
            analyzer="word", token_pattern=r"[a-z0-9\u00f1]+", lowercase=False,
            ngram_range=(1, 2), sublinear_tf=True,
        )
        self.word.fit(primary + body + full)
        self.P = self.word.transform([f"{p} {t}".strip() for p, t in zip(primary, tag)])
        self.B = self.word.transform(body)

        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, lowercase=False)
        self.char.fit(full)
        self.C = self.char.transform(full)

        names = self.word.get_feature_names_out()
        self.idf = {n: w for n, w in zip(names, self.word.idf_) if " " not in n}
        self.max_idf = max(self.idf.values()) if self.idf else 1.0

    def score(self, query_text, query_tokens, free_topics=frozenset()):
        """
        Returns a list of (score 0-1, missed_topic) tuples, one per doc.
        free_topics are topic words that need not appear in the document
        (e.g. "price" for products, since price is always in the catalog).
        """
        if not query_tokens or not self.docs:
            return [(0.0, False)] * len(self.docs)

        qw = self.word.transform([query_text])
        cos_primary = cosine_similarity(qw, self.P)[0]
        cos_body = cosine_similarity(qw, self.B)[0]
        cos_char = cosine_similarity(self.char.transform([query_text]), self.C)[0]

        # Words the knowledge base has never seen (a bike model, a street name) should
        # not drag a good match down, so they count for a fraction of a known word.
        weights = {}
        for t in set(query_tokens):
            if t in self.idf:
                weights[t] = self.idf[t]
            elif any(ch.isdigit() for ch in t):
                weights[t] = self.max_idf * UNKNOWN_NUMBER_WEIGHT
            else:
                weights[t] = self.max_idf * UNKNOWN_WORD_WEIGHT
        total = sum(weights.values()) or 1.0

        topics = (_topic_stems() - {_stem(t) for t in free_topics}) & set(query_tokens)

        scores = []
        for i in range(len(self.docs)):
            covered = sum(w for t, w in weights.items() if t in self.token_sets[i])
            in_title = sum(w for t, w in weights.items() if t in self.primary_sets[i])
            coverage = covered / total
            title_coverage = in_title / total
            cosine = 0.65 * cos_primary[i] + 0.35 * cos_body[i]
            final = (
                0.30 * cosine
                + 0.15 * cos_char[i]
                + 0.30 * coverage
                + 0.25 * title_coverage
            )
            missed = [t for t in topics if t not in self.token_sets[i]]
            if missed:
                final *= MISSED_TOPIC_PENALTY ** len(missed)
            scores.append((float(min(final, 1.0)), bool(missed)))
        return scores


_INDEX_CACHE = {}


def _get_index(kind, docs):
    key_src = kind + "|" + "|".join(f"{d.ref.id}:{d.primary}:{d.body}:{d.tag}" for d in docs)
    key = hashlib.md5(key_src.encode("utf-8")).hexdigest()
    index = _INDEX_CACHE.get(key)
    if index is None:
        if len(_INDEX_CACHE) > 8:
            _INDEX_CACHE.clear()
        index = _Index(docs)
        _INDEX_CACHE[key] = index
    return index


def _rank(kind, docs, query_text, query_tokens, free_topics=frozenset()):
    """Returns [(ref, score, missed_topic)] sorted best first."""
    if not docs:
        return []
    index = _get_index(kind, docs)
    scores = index.score(query_text, query_tokens, free_topics)
    ranked = sorted(zip(docs, scores), key=lambda pair: pair[1][0], reverse=True)
    return [(d.ref, sc, missed) for d, (sc, missed) in ranked]

# Public helpers

def _kb_docs(entries, include_pending):
    pool = entries if include_pending else [e for e in entries if e.status == "approved"]
    return [_Doc(e, e.question, e.answer, e.category) for e in pool]


def _product_docs(products):
    docs = []
    for p in products or []:
        parts = [p.short_desc, p.description]
        for field in (p.specs, p.benefits, p.usage_steps):
            if isinstance(field, (list, tuple)):
                parts.extend(str(x) for x in field)
        docs.append(_Doc(p, p.name, " ".join(x for x in parts if x), p.category))
    return docs


def retrieve(question, entries, include_pending=False):
    """
    Knowledge-base only retrieval (kept for backwards compatibility).
    Returns (matched_entry_or_None, confidence_percent, candidates) where
    candidates is a list of (entry, score) for the top 3 matches.
    """
    docs = _kb_docs(entries, include_pending)
    if not docs:
        return None, 0, []
    text, tokens, _, _ = _analyze(question)
    ranked = _rank("kb", docs, text, tokens)
    if not ranked:
        return None, 0, []
    top_entry, top_score, _ = ranked[0]
    matched = top_entry if top_score >= KB_ANSWER_MIN else None
    return matched, round(top_score * 100), [(e, sc) for e, sc, _ in ranked[:3]]


def _peso(value):
    return "\u20b1{:,.2f}".format(float(value))


def _stock_phrase(product):
    stock = int(product.stock or 0)
    if stock <= 0:
        return "It's currently out of stock."
    if stock < 20:
        return f"It's in stock, but only {stock} left."
    return f"It's in stock ({stock} available)."


def _compose_product_answer(products, intents):
    """Builds an answer from live catalog data. `products` is 1-3 Product rows."""
    if len(products) == 1:
        p = products[0]
        specs = [str(s) for s in (p.specs or [])]
        usage = [str(s) for s in (p.usage_steps or [])]

        if "specs" in intents and specs:
            lines = "\n".join(f"\u2022 {s}" for s in specs)
            return f"Here are the specs for {p.name}:\n{lines}\nPrice: {_peso(p.price)}."
        if "usage" in intents and usage:
            lines = "\n".join(f"{i}. {s}" for i, s in enumerate(usage, 1))
            return f"How to use {p.name}:\n{lines}"
        if "stock" in intents and "price" not in intents:
            return f"{p.name}: {_stock_phrase(p)} Price: {_peso(p.price)}."
        if "price" in intents:
            return f"{p.name} is {_peso(p.price)}. {_stock_phrase(p)}"
        return f"{p.name} \u2014 {p.short_desc} Price: {_peso(p.price)}. {_stock_phrase(p)}"

    lines = []
    for p in products:
        stock = int(p.stock or 0)
        status = "out of stock" if stock <= 0 else "in stock"
        lines.append(f"\u2022 {p.name} \u2014 {_peso(p.price)} ({status})")
    header = "Here are the matching products:"
    if "stock" in intents and "price" not in intents:
        header = "Here is the availability of the matching products:"
    return header + "\n" + "\n".join(lines) + "\nTell me which one you'd like to know more about."


def _smalltalk(raw_tokens, content_tokens):
    """Greetings / thanks / bye. Only used when there is no real question."""
    if content_tokens or not raw_tokens:
        return None
    words = set(raw_tokens)
    if words & {"thanks", "thank", "thankyou", "ty", "salamat"} and words <= _THANKS:
        return "You're welcome! Let me know if there's anything else I can help you with."
    if words & _BYE and words <= (_BYE | _THANKS | _GREETINGS):
        return "Thanks for chatting with Rainchem! Ride safe."
    if words <= _GREETINGS:
        return (
            "Hi! I'm the Rainchem assistant. Ask me about engine oil, RadCool coolant, "
            "prices, delivery, payment, or your orders. You can ask in English or Tagalog."
        )
    return None


def _result(answer, source, confidence=0, matched=None, resolved=True, candidates=None, related=None,
            products=None, can_rate=True):
    return {
        "answer": answer,
        "source": source,
        "matched_entry": matched,
        "matched_products": products or [],
        "confidence": confidence,
        "resolved": resolved,
        "can_rate": can_rate,
        "candidates": [
            {"question": e.question, "score": round(score * 100)} for e, score in (candidates or [])
        ],
        "related": [{"id": e.id, "question": e.question} for e in (related or [])],
    }


def answer_question(question, entries, products=None, previous_question=None, include_pending=False):
    """
    Main entry point used by the chat route and the admin tester.

    Returns a dict with: answer, source ("knowledge" | "product" | "smalltalk" |
    "fallback"), matched_entry, matched_products, confidence (0-100),
    resolved, can_rate, candidates (top 3 knowledge matches) and related
    (suggested follow-up knowledge entries).
    """
    text, tokens, intents, raw = _analyze(question)

    talk = _smalltalk(raw, tokens)
    if talk:
        return _result(talk, "smalltalk", confidence=100, can_rate=False)
    if not tokens:
        return _result(REPHRASE_ANSWER, "fallback", resolved=False, can_rate=True)

    kb_docs = _kb_docs(entries, include_pending)
    prod_docs = _product_docs(products)

    def run(q_text, q_tokens):
        return (
            _rank("kb", kb_docs, q_text, q_tokens),
            _rank("product", prod_docs, q_text, q_tokens, free_topics={"price", "stock", "discount"}),
        )

    kb_ranked, prod_ranked = run(text, tokens)
    kb_score = kb_ranked[0][1] if kb_ranked else 0.0
    prod_score = prod_ranked[0][1] if prod_ranked else 0.0

    # Short follow-ups like "how about the semi-synthetic?" borrow context
    # from the user's previous question.
    # Only when the new question has no clear match of its own: otherwise a
    # self-contained question ("magkano ang radcool?") would get mixed up with
    # whatever was asked before it.
    if previous_question and len(tokens) <= 2 and kb_score < SUGGEST_MIN and prod_score < PRODUCT_MIN:
        prev_text, prev_tokens, prev_intents, _ = _analyze(previous_question)
        merged_text = f"{prev_text} {text}".strip()
        merged_tokens = prev_tokens + tokens
        m_kb, m_prod = run(merged_text, merged_tokens)
        m_kb_score = m_kb[0][1] if m_kb else 0.0
        m_prod_score = m_prod[0][1] if m_prod else 0.0
        if max(m_kb_score, m_prod_score) > max(kb_score, prod_score):
            kb_ranked, prod_ranked = m_kb, m_prod
            kb_score, prod_score = m_kb_score, m_prod_score
            intents = intents | prev_intents

    candidates = [(e, sc) for e, sc, _ in kb_ranked[:3]]
    commerce_intent = bool(intents & {"price", "stock", "specs", "usage"})

    # 0) Very short, generic question with several equally good matches.
    if len(raw) <= CLARIFY_MAX_TOKENS:
        best = max(kb_score, prod_score)
        options = []
        for e, sc, missed in kb_ranked[:3]:
            if not missed and sc >= KB_ANSWER_MIN and sc >= best - CLARIFY_MARGIN:
                options.append({"id": e.id, "question": e.question})
        for p, sc, _ in prod_ranked[:3]:
            if sc >= PRODUCT_MIN and sc >= best - CLARIFY_MARGIN:
                options.append({"id": None, "question": p.name})
        if len(options) >= 2 and not commerce_intent:
            options = options[:4]
            message = CLARIFY_ANSWER_TL if _looks_tagalog(raw) else CLARIFY_ANSWER
            result = _result(message, "clarify", confidence=round(max(kb_score, prod_score) * 100),
                             resolved=False, candidates=candidates, can_rate=False)
            result["related"] = options
            return result

    # 1) Product answer: the user asked about price/stock/specs of something
    #    we sell, or named a product far more strongly than any FAQ matches.
    use_product = False
    if prod_ranked and prod_score >= PRODUCT_MIN:
        if commerce_intent and prod_score >= kb_score * 0.6:
            use_product = True
        elif prod_score >= 0.5 and prod_score > kb_score + 0.15:
            use_product = True
    if use_product:
        group = [
            p for p, sc, _ in prod_ranked[:3]
            if sc >= prod_score * PRODUCT_GROUP_RATIO and sc >= PRODUCT_MIN
        ]
        if len(group) > 1 and prod_ranked[0][1] - prod_ranked[1][1] > 0.12:
            group = group[:1]
        answer = _compose_product_answer(group, intents)
        return _result(answer, "product", confidence=round(prod_score * 100),
                       candidates=candidates, products=group)

    # 2) Knowledge base answer.
    if kb_ranked and kb_score >= KB_ANSWER_MIN:
        matched = kb_ranked[0][0]
        related = [
            e for e, sc, missed in kb_ranked[1:4]
            if not missed and sc >= max(SUGGEST_MIN, kb_score * 0.55) and e.id != matched.id
        ][:2]
        return _result(matched.answer, "knowledge", confidence=round(kb_score * 100),
                       matched=matched, candidates=candidates, related=related)

    # 3) Not sure: offer suggestions instead of a wrong answer. Entries that
    #    miss a key topic of the question are never suggested.
    suggestions = [e for e, sc, missed in kb_ranked[:3] if sc >= SUGGEST_MIN and not missed]
    tagalog = _looks_tagalog(raw)
    if suggestions:
        message = FALLBACK_WITH_SUGGESTIONS_TL if tagalog else FALLBACK_WITH_SUGGESTIONS
    else:
        message = FALLBACK_ANSWER_TL if tagalog else FALLBACK_ANSWER
    return _result(message, "fallback", confidence=round(kb_score * 100), resolved=False,
                   candidates=candidates, related=suggestions)
