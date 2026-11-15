"""Measures the recommender against evaluation/cases.py and the test fixtures.

Run it from the backend folder:   python -m evaluation.run
It builds a throw-away in-memory database, so it never touches real data."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Product, ProductDocument  # noqa: E402
from app.services import recommender  # noqa: E402
from config import TestConfig  # noqa: E402
from evaluation.cases import CASES, ODD_INPUTS, RELEVANCE_K, THRESHOLDS  # noqa: E402
from evaluation.fixtures import DOCUMENTS, PRODUCTS  # noqa: E402


def load_fixtures():
    products = {}
    for name, category, price in PRODUCTS:
        product = Product(name=name, category=category, price=price, stock=20, short_desc=name, description=name, specs=[], benefits=[], usage_steps=[])
        db.session.add(product)
        products[name] = product
    db.session.flush()
    for name, (title, doc_type, version, source, content, facts, verified, authorized) in DOCUMENTS.items():
        db.session.add(ProductDocument(
            product_id=products[name].id, title=title, doc_type=doc_type, version=version, source=source,
            content=content, facts=facts, verified=verified, authorized=authorized, verified_by="Test" if verified else None,
        ))
    db.session.commit()
    return products


def converse(turns):
    context, replies = None, []
    for text in turns:
        started = time.perf_counter()
        reply = recommender.recommend(text, context, log=False)
        reply["_ms"] = (time.perf_counter() - started) * 1000
        replies.append(reply)
        context = reply["context"]
    return replies


def retrieval_rank(slots, wanted_names):
    """Where the expected products land when documents are ranked by text similarity alone (before the rule checks)."""
    docs = recommender.usable_documents()
    chunks = [{"product_id": d.product_id, "text": c} for d in docs for c in recommender._chunks(d.content + " " + recommender._facts_text(d))]
    index = recommender._Index(chunks)
    query = " ".join([recommender.APPLICATION_LABELS.get(slots.get("application"), ""), slots.get("equipment", ""), slots.get("engine_type", "")]
                     + slots.get("viscosity", []) + slots.get("standards", []))
    best = {}
    for chunk, score in zip(chunks, index.score(query)):
        best[chunk["product_id"]] = max(best.get(chunk["product_id"], 0), score)
    ranked = [pid for pid, _ in sorted(best.items(), key=lambda kv: -kv[1])]
    names = {p.id: p.name for p in Product.query.all()}
    ranked_names = [names[p] for p in ranked]
    return all(name in ranked_names[:RELEVANCE_K] for name in wanted_names)


def evidence_is_real(card):
    """Every piece of evidence and every source must come from a document that is verified and authorised."""
    usable = {d.id: d for d in recommender.usable_documents()}
    for source in card["sources"]:
        doc = usable.get(source["documentId"])
        if doc is None or doc.title != source["title"] or doc.version != source["version"]:
            return False
    for item in card["matched"]:
        docs = [usable[s["documentId"]] for s in card["sources"] if s["documentId"] in usable]
        haystack = " ".join(d.content + " " + recommender._facts_text(d) for d in docs).lower()
        text = item["evidence"].rstrip(".").lower().replace("...", "")
        if text.split(": ", 1)[-1] not in haystack and text not in haystack:
            return False
    return True


def evaluate():
    results, times, errors = [], [], 0
    checks = {"exact": [], "retrieval": [], "sources": [], "refusal": [], "missing": [], "unverified": []}
    for case in CASES:
        try:
            replies = converse(case["turns"])
        except Exception as error:  # noqa: BLE001
            errors += 1
            results.append({"id": case["id"], "passed": False, "error": repr(error)})
            continue
        final = replies[-1]
        times += [r["_ms"] for r in replies]
        names = [c["name"] for c in final["recommendations"]]
        passed = final["status"] == case["expect"]
        detail = {"id": case["id"], "expected": case["expect"], "got": final["status"], "products": names}

        if case["expect"] == "matches":
            exact = set(names) == set(case["products"])
            checks["exact"].append(exact)
            passed = passed and exact
            checks["retrieval"].append(retrieval_rank(final["requirements"], case["products"]))
            checks["sources"] += [evidence_is_real(c) and bool(c["sources"]) for c in final["recommendations"]]
            if case.get("limitation") == "viscosity":
                ok = all(any("viscosity" in l.lower() for l in c["limitations"]) for c in final["recommendations"])
                checks["missing"].append(ok)
                passed = passed and ok
        elif case["expect"] == "insufficient":
            ok = final["status"] == "insufficient" and final["needsHuman"] and not final["recommendations"] and "technical confirmation" in final["answer"].lower()
            checks["refusal"].append(ok)
            passed = passed and ok
        elif case["expect"] == "needs_info":
            ok = bool(final["question"]) and not final["recommendations"]
            checks["missing"].append(ok)
            passed = passed and ok
        for forbidden in case.get("never", []):
            checks["unverified"].append(forbidden not in names and forbidden not in final["answer"])
            passed = passed and checks["unverified"][-1]
        detail["passed"] = passed
        results.append(detail)

    for text in ODD_INPUTS:
        for context in (None, {"slots": {"application": "engine_oil"}, "asked": ["equipment"], "turns": 1}):
            started = time.perf_counter()
            try:
                reply = recommender.recommend(text, context, log=False)
                assert reply["status"] in ("needs_info", "matches", "insufficient")
            except Exception:  # noqa: BLE001
                errors += 1
            times.append((time.perf_counter() - started) * 1000)

    rate = lambda xs: (sum(xs) / len(xs)) if xs else 1.0
    metrics = {
        "cases": len(CASES), "cases_passed": sum(1 for r in results if r["passed"]),
        "product_exact_match": round(rate(checks["exact"]), 3), "retrieval_hit_at_k": round(rate(checks["retrieval"]), 3),
        "source_validity": round(rate(checks["sources"]), 3), "refusal": round(rate(checks["refusal"]), 3),
        "missing_info_handling": round(rate(checks["missing"]), 3), "unverified_never_used": round(rate(checks["unverified"]), 3),
        "errors": errors, "avg_ms": round(sum(times) / len(times), 1), "max_ms": round(max(times), 1), "calls": len(times),
    }
    return metrics, results


def main():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        load_fixtures()
        metrics, results = evaluate()
    print(f"{'case':32} {'expected':13} {'got':13} result")
    for r in results:
        print(f"{r['id']:32} {r.get('expected', ''):13} {r.get('got', ''):13} {'ok' if r['passed'] else 'FAILED'} {r.get('products', '')}")
    print()
    for key, value in metrics.items():
        limit = THRESHOLDS.get(key)
        flag = "" if limit is None else ("  (limit %s)" % limit)
        print(f"{key:24} {value}{flag}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_report.json"), "w") as handle:
        json.dump({"metrics": metrics, "cases": results}, handle, indent=2)
    failed = [r for r in results if not r["passed"]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
