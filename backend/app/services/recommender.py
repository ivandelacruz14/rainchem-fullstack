"""Guided product matching from verified product documentation.

What it does: it reads the customer's requirements, asks for what is missing, then looks only at documents that a
Head Admin has verified and authorised. A product is recommended only when the documents confirm every requirement
the customer gave. Everything shown (specifications, sources, evidence) is copied from those documents. There is no
text generation, so nothing can be invented, and the customer's words are only searched for keywords: they are never
treated as instructions."""
import math
import re
import time
from collections import Counter

from app.extensions import db
from app.models import Product, ProductDocument, RecommendationLog

MAX_TURNS = 4
MAX_RESULTS = 3
EXCERPT_LENGTH = 220

APPLICATIONS = {
    "engine_oil": ("engine oil", "motor oil", "oil change", "langis ng makina", "engine lubricant", "engine"),
    "gear_oil": ("gear oil", "gearbox", "transmission oil", "transmission fluid", "differential"),
    "coolant": ("coolant", "antifreeze", "anti-freeze", "radiator fluid", "radiator"),
    "brake_fluid": ("brake fluid", "brake oil"),
    "grease": ("grease",),
    "hydraulic_oil": ("hydraulic",),
    "chain_lube": ("chain lube", "chain lubricant", "chain spray"),
}
APPLICATION_LABELS = {
    "engine_oil": "engine oil", "gear_oil": "gear oil", "coolant": "coolant", "brake_fluid": "brake fluid",
    "grease": "grease", "hydraulic_oil": "hydraulic oil", "chain_lube": "chain lubricant",
}
EQUIPMENT = {
    "motorcycle": ("motorcycle", "motorbike", "scooter", "underbone", "big bike", "bike", "motor ko", "tricycle"),
    "car": ("car", "sedan", "suv", "hatchback", "pickup", "van", "kotse"),
    "truck": ("truck", "lorry", "trak"),
    "jeepney": ("jeepney", "jeep"),
    "generator": ("generator", "genset"),
    "machinery": ("machine", "machinery", "compressor", "pump", "equipment"),
}
ENGINE_TYPES = {
    "2-stroke": (r"\b2[- ]?stroke\b", r"\btwo[- ]?stroke\b", r"\b2t\b"),
    "4-stroke": (r"\b4[- ]?stroke\b", r"\bfour[- ]?stroke\b", r"\b4t\b"),
    "diesel": (r"\bdiesel\b",),
    "gasoline": (r"\bgasoline\b", r"\bpetrol\b", r"\bunleaded\b"),
}
COMPATIBILITY = ("wet clutch", "dry clutch", "catalytic converter", "turbo", "turbocharged", "dpf", "high mileage")
UNSURE = re.compile(r"\b(not sure|don'?t know|do not know|no idea|unsure|skip|none|wala|hindi ko alam|di ko alam)\b")
INTENT = re.compile(
    r"\b(recommend|suggest|suitable|best (oil|lubricant|coolant|product)|which (oil|lubricant|coolant|product)|"
    r"what (oil|lubricant|coolant|product|should i use)|anong (langis|produkto)|ano ang (langis|gamit)|"
    r"right (oil|lubricant)|compatible with my|good for my|para sa (motor|kotse)|pang(?:-| )?gamit)\b"
)
STOPWORDS = set("""a an the and or of for to in on at is are be my your our i me it this that with from by as do does can could
please what which should would use using need want help about any some have has had not no yes""".split())

ENGINE_QUESTION = "What type of engine does it have (2-stroke, 4-stroke, gasoline or diesel)?"
SPEC_QUESTION = ("Does your manufacturer recommend a viscosity grade or specification, for example 10W-40 or JASO MA2? "
                 "If you are not sure, tell me and I will use what I have.")
QUESTIONS = {
    "engine_type": ENGINE_QUESTION,
    "equipment": "What equipment or vehicle will use the product (for example a motorcycle, a car or a generator)?",
    "application": "What will the product be used for (for example engine oil, gear oil or coolant)?",
    "spec": SPEC_QUESTION,
}


# ------------------------------------------------------------------ understanding the request

def looks_like_recommendation_request(text):
    return bool(INTENT.search((text or "").lower()))


def parse_requirements(text):
    """Pulls out what the customer said they need. Only keywords and codes are read."""
    t = f" {(text or '').lower()} "
    found = {}
    best = (0, None)
    for key, words in APPLICATIONS.items():
        for w in words:
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) and len(w) > best[0]:
                best = (len(w), key)
    if best[1]:
        found["application"] = best[1]
    for key, words in EQUIPMENT.items():
        if any(re.search(rf"\b{re.escape(w)}\b", t) for w in words):
            found["equipment"] = key
            break
    for key, patterns in ENGINE_TYPES.items():
        if any(re.search(p, t) for p in patterns):
            found["engine_type"] = key
            break
    grades = [re.sub(r"[ -]", "", m.upper()).replace("W", "W-") for m in re.findall(r"\b(\d{1,2}\s?w[- ]?\d{2})\b", t)]
    iso = [f"ISO VG {n}" for n in re.findall(r"\biso\s*vg\s*(\d{2,4})\b", t)]
    sae = [f"SAE {n}" for n in re.findall(r"\bsae\s*(\d{2,3})\b(?!\s*w)", t)]
    if grades or iso or sae:
        found["viscosity"] = list(dict.fromkeys(grades + iso + sae))
    standards = [f"API {m.upper()}" for m in re.findall(r"\bapi\s+(s[a-z]|c[a-z]-?\d?)\b", t)]
    standards += [f"JASO {m.upper()}" for m in re.findall(r"\bjaso\s+(ma2|ma|mb|fd|fb)\b", t)]
    standards += [f"ACEA {m.upper()}" for m in re.findall(r"\bacea\s+([a-e]\d)\b", t)]
    standards += [f"DOT {m}" for m in re.findall(r"\bdot\s*(3|4|5\.1)\b", t)]
    if standards:
        found["standards"] = list(dict.fromkeys(standards))
    notes = [w for w in COMPATIBILITY if w in t]
    if notes:
        found["compatibility"] = notes
    if UNSURE.search(t):
        found["unsure"] = True
    return found


def merge_context(context, parsed):
    slots = dict((context or {}).get("slots", {}))
    for key, value in parsed.items():
        if key == "unsure":
            continue
        slots[key] = list(dict.fromkeys(list(slots.get(key, [])) + value)) if isinstance(value, list) else value
    return slots


def next_question(slots, asked, unsure):
    """What to ask next, if anything. Only things that matter for the match are asked, each at most once."""
    if "equipment" not in slots and "engine_type" not in slots and "equipment" not in asked:
        return "equipment"
    if "application" not in slots and "application" not in asked:
        return "application"
    if slots.get("application") == "engine_oil" and "engine_type" not in slots and "engine_type" not in asked:
        return "engine_type"   # the wrong kind of engine oil can damage an engine, so this always matters
    ready = ("equipment" in slots or "engine_type" in slots) and "application" in slots
    if ready and "viscosity" not in slots and "standards" not in slots and "spec" not in asked and not unsure:
        return "spec"
    return None


# ------------------------------------------------------------------ searching the documents

def _tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", (text or "").lower()) if w not in STOPWORDS and len(w) > 1]


def _chunks(content):
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n(?=[-*\u2022])", content or "") if p.strip()]
    chunks = []
    for part in parts:
        while len(part) > 500:
            cut = part.rfind(". ", 0, 500)
            cut = cut + 1 if cut > 100 else 500
            chunks.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            chunks.append(part)
    return chunks


class _Index:
    """A small TF-IDF index over document chunks. Used to rank, never to decide on its own."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.docs = [Counter(_tokens(c["text"])) for c in chunks]
        df = Counter(t for d in self.docs for t in d)
        n = max(len(self.docs), 1)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.norms = [math.sqrt(sum((tf * self.idf[t]) ** 2 for t, tf in d.items())) or 1.0 for d in self.docs]

    def score(self, query_text):
        q = Counter(_tokens(query_text))
        qn = math.sqrt(sum((tf * self.idf.get(t, 1.0)) ** 2 for t, tf in q.items())) or 1.0
        scores = []
        for d, norm in zip(self.docs, self.norms):
            dot = sum(tf * self.idf.get(t, 1.0) * d[t] * self.idf.get(t, 1.0) for t, tf in q.items() if t in d)
            scores.append(dot / (qn * norm))
        return scores


def usable_documents():
    return ProductDocument.query.filter_by(verified=True, authorized=True).filter(ProductDocument.product_id.isnot(None)).all()


def _word(term, text):
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", (text or "").lower()))


def _excerpt(content, terms):
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", content or ""):
        if any(_word(t, sentence) for t in terms):
            s = sentence.strip()
            return s if len(s) <= EXCERPT_LENGTH else s[:EXCERPT_LENGTH - 3] + "..."
    return None


def _facts_text(doc):
    facts = doc.facts or {}
    return " ; ".join(f"{k}: {', '.join(v)}" for k, v in facts.items() if v)


def _has(doc, term, fact_keys):
    """Does this document confirm the term? Returns evidence text, or None. Structured facts come first."""
    facts = doc.facts or {}
    for key in fact_keys:
        for value in facts.get(key, []):
            if _word(term, value) or _word(value, term):
                return f"{key.replace('_', ' ').capitalize()}: {value}"
    return _excerpt(doc.content, [term])


def _conflict(doc, terms):
    for value in (doc.facts or {}).get("not_for", []):
        if any(_word(t, value) or _word(value, t) for t in terms):
            return value
    return None


def _check_product(docs, slots):
    """Compares what the customer asked for with what this product's documents confirm."""
    confirmed, unmet, conflicts = [], [], []

    def look(requirement, term, fact_keys):
        for doc in docs:
            evidence = _has(doc, term, fact_keys)
            if evidence:
                confirmed.append({"requirement": requirement, "evidence": evidence, "documentId": doc.id})
                return True
        unmet.append(requirement)
        return False

    app = slots.get("application")
    if app:
        label = APPLICATION_LABELS[app]
        terms = APPLICATIONS[app]
        hit = False
        for doc in docs:
            for term in (label,) + terms:
                evidence = _has(doc, term, ("applications",))
                if evidence:
                    confirmed.append({"requirement": f"Used as {label}", "evidence": evidence, "documentId": doc.id})
                    hit = True
                    break
            if hit:
                break
        if not hit:
            unmet.append(f"Used as {label}")
    for key, fact_keys in (("equipment", ("equipment", "applications")), ("engine_type", ("engine_types", "applications"))):
        value = slots.get(key)
        if value:
            terms = list(dict.fromkeys([value] + list(EQUIPMENT.get(value, ())))) if key == "equipment" else [value]
            for doc in docs:
                bad = _conflict(doc, terms)
                if bad:
                    conflicts.append(f"{doc.title} says it is not for {bad}")
            if not conflicts:
                hit = False
                for term in terms:
                    for doc in docs:
                        evidence = _has(doc, term, fact_keys)
                        if evidence:
                            confirmed.append({"requirement": f"For {value}", "evidence": evidence, "documentId": doc.id})
                            hit = True
                            break
                    if hit:
                        break
                if not hit:
                    unmet.append(f"For {value}")
    for grade in slots.get("viscosity", []):
        look(f"Viscosity {grade}", grade, ("viscosity_grades",))
    for standard in slots.get("standards", []):
        look(f"Meets {standard}", standard, ("standards",))
    for note in slots.get("compatibility", []):
        look(f"Compatible with {note}", note, ("compatible_with",))
    return confirmed, unmet, conflicts


def _summary_of_facts(docs):
    merged = {}
    for doc in docs:
        for key, values in (doc.facts or {}).items():
            if key == "warnings":
                continue
            merged.setdefault(key, [])
            merged[key] += [v for v in values if v not in merged[key]]
    labels = {"viscosity_grades": "Viscosity grades", "standards": "Standards", "applications": "Applications",
              "equipment": "Equipment", "engine_types": "Engine types", "compatible_with": "Compatible with"}
    return [{"label": labels[k], "values": v} for k, v in merged.items() if v and k in labels]


def match(slots, documents=None):
    documents = usable_documents() if documents is None else documents
    by_product = {}
    for doc in documents:
        by_product.setdefault(doc.product_id, []).append(doc)
    products = {p.id: p for p in Product.query.filter(Product.id.in_(list(by_product)), Product.category != "Services").all()} if by_product else {}

    chunks = [{"product_id": d.product_id, "doc_id": d.id, "text": c} for d in documents for c in _chunks(d.content + " " + _facts_text(d))]
    index = _Index(chunks) if chunks else None
    query = " ".join(
        [APPLICATION_LABELS.get(slots.get("application"), ""), slots.get("equipment", ""), slots.get("engine_type", "")]
        + slots.get("viscosity", []) + slots.get("standards", []) + slots.get("compatibility", [])
    )
    scores = index.score(query) if index and query.strip() else []
    best_for = {}
    for chunk, score in zip(chunks, scores):
        best_for[chunk["product_id"]] = max(best_for.get(chunk["product_id"], 0.0), score)

    suitable, unconfirmed = [], []
    for pid, docs in by_product.items():
        product = products.get(pid)
        if product is None:
            continue
        confirmed, unmet, conflicts = _check_product(docs, slots)
        if conflicts:
            continue
        entry = {"product": product, "docs": docs, "confirmed": confirmed, "unmet": unmet, "score": best_for.get(pid, 0.0)}
        if confirmed and not unmet:
            suitable.append(entry)
        elif confirmed:
            unconfirmed.append(entry)
    suitable.sort(key=lambda e: (-len(e["confirmed"]), -e["score"], e["product"].name))
    return suitable[:MAX_RESULTS], unconfirmed


# ------------------------------------------------------------------ the answer

def _describe(slots):
    bits = []
    if slots.get("application"):
        bits.append(APPLICATION_LABELS[slots["application"]])
    for_what = slots.get("equipment") or slots.get("engine_type")
    if for_what:
        bits.append(f"for a {for_what}" if slots.get("equipment") else f"for a {for_what} engine")
    if slots.get("viscosity"):
        bits.append("grade " + ", ".join(slots["viscosity"]))
    if slots.get("standards"):
        bits.append("meeting " + ", ".join(slots["standards"]))
    return " ".join(bits)


def _card(entry, slots):
    product = entry["product"]
    limits = []
    if not (slots.get("viscosity") or slots.get("standards")):
        limits.append("You did not give a viscosity grade or specification. Check your manufacturer's manual to be sure it is the one it asks for.")
    for doc in entry["docs"]:
        limits += [f"{doc.title}: {w}" for w in (doc.facts or {}).get("warnings", [])]
    return {
        "productId": product.id, "name": product.name, "category": product.category, "price": float(product.price),
        "link": f"/shop?product={product.id}", "inStock": product.stock > 0,
        "matched": [{"requirement": c["requirement"], "evidence": c["evidence"]} for c in entry["confirmed"]],
        "specs": _summary_of_facts(entry["docs"]),
        "sources": [{"documentId": d.id, "title": d.title, "type": d.doc_type, "version": d.version, "source": d.source} for d in entry["docs"]],
        "limitations": limits,
    }


def _log(status, slots, cards, docs, score, started):
    db.session.add(RecommendationLog(
        status=status, application=slots.get("application"),
        slots_given=sorted(k for k in slots if k != "unsure"),
        product_ids=[c["productId"] for c in cards], document_ids=sorted({d.id for e in docs for d in e["docs"]}) if docs else [],
        top_score=round(score, 3) if score else None, elapsed_ms=int((time.perf_counter() - started) * 1000),
    ))
    db.session.commit()


def recommend(message, context=None, log=True):
    """One turn of the guided conversation. Returns the reply and the context to send back next time."""
    started = time.perf_counter()
    context = context if isinstance(context, dict) else {}
    parsed = parse_requirements(message)
    asked = list(context.get("asked", []))
    last_asked = asked[-1] if asked else None
    if last_asked == "equipment" and "equipment" not in parsed and "engine_type" not in parsed and not parsed.get("unsure"):
        free = re.sub(r"\s+", " ", (message or "").strip().lower())[:60]
        if free and len(free.split()) <= 6:
            parsed["equipment"] = free          # e.g. a model name; it must then be found in the documents
    slots = merge_context(context, parsed)
    turns = int(context.get("turns", 0)) + 1
    question = next_question(slots, asked, bool(parsed.get("unsure")) or "unsure" in asked)

    if question and turns <= MAX_TURNS:
        asked.append(question)
        if parsed.get("unsure"):
            asked.append("unsure")
        reply = {
            "status": "needs_info", "question": QUESTIONS[question], "answer": QUESTIONS[question],
            "recommendations": [], "missing": [], "needsHuman": False,
            "context": {"slots": slots, "asked": asked, "turns": turns},
        }
        if log:
            _log("needs_info", slots, [], [], 0, started)
        return reply

    suitable, unconfirmed = match(slots) if ("application" in slots and ("equipment" in slots or "engine_type" in slots)) else ([], [])
    cards = [_card(e, slots) for e in suitable]
    missing = []
    if not (slots.get("viscosity") or slots.get("standards")):
        missing.append("Viscosity grade or specification recommended by your manufacturer")
    if "application" not in slots:
        missing.append("What the product will be used for")
    if "equipment" not in slots and "engine_type" not in slots:
        missing.append("The equipment or vehicle")

    if cards:
        names = "; ".join(c["name"] for c in cards)
        answer = (f"Based on our verified product documentation, these products match your requirements ({_describe(slots)}): {names}. "
                  "Each one below shows why it matches and where that information comes from. "
                  "This is guidance from the documents, so always follow your manufacturer's recommendation.")
        status, human = "matches", False
        score = max(e["score"] for e in suitable)
    else:
        extra = ""
        if unconfirmed:
            extra = (" I found products that match part of your request, but the documents do not confirm all of it: "
                     + "; ".join(f"{e['product'].name} (not confirmed: {', '.join(e['unmet'])})" for e in unconfirmed[:3]) + ".")
        answer = ("I can't confirm a suitable product from our verified documentation yet." + extra +
                  " Technical confirmation is required. Our admin or technical team can check this for you.")
        status, human, score = "insufficient", True, 0.0

    if log:
        _log(status, slots, cards, suitable, score, started)
    return {
        "status": status, "answer": answer, "question": None, "recommendations": cards, "missing": missing,
        "notConfirmed": [{"name": e["product"].name, "unmet": e["unmet"]} for e in unconfirmed[:3]] if not cards else [],
        "needsHuman": human, "requirements": slots, "confidence": min(100, int(60 + 40 * score)) if cards else 0,
        "context": None,
    }
