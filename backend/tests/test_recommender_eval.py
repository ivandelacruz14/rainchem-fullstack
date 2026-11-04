from evaluation.cases import THRESHOLDS
from evaluation.run import evaluate, load_fixtures


def test_the_recommender_meets_its_evaluation_targets(app):
    load_fixtures()
    metrics, results = evaluate()
    failed = [r for r in results if not r["passed"]]
    assert not failed, failed
    assert metrics["errors"] <= THRESHOLDS["errors"]
    for key in ("product_exact_match", "retrieval_hit_at_k", "source_validity", "refusal", "missing_info_handling", "unverified_never_used"):
        assert metrics[key] >= THRESHOLDS[key], (key, metrics[key])
    assert metrics["max_ms"] <= THRESHOLDS["max_ms"]
