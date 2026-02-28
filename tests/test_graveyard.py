from __future__ import annotations

from cortex.genome import GraveyardConfig
from cortex.graveyard import Graveyard
from cortex.store import SQLiteStore


def test_similarity_match_on_keyword_overlap(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.2))
    g.record_failure(
        "sess-1",
        "Virtualized member list",
        "Broke sticky header and scrolling behavior",
        files=["src/member_list.tsx"],
    )
    matches = g.find_similar("member list sticky header regression", ["src/member_list.tsx"])
    assert matches
    assert matches[0].summary == "Virtualized member list"
    assert "sticky" in matches[0].keyword_overlap


def test_no_match_on_non_overlapping_keywords(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.2))
    g.record_failure("sess-1", "Cache warming", "Timeout in redis startup", files=["src/cache.py"])
    assert g.find_similar("ui layout spacing issue", ["src/ui.tsx"]) == []


def test_threshold_filters_low_similarity(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.95))
    g.record_failure("sess-1", "Handle null user", "Null body caused parse crash", files=["src/api.py"])
    assert g.find_similar("null user parse", ["src/other.py"]) == []


def test_max_matches_limits_results(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.1, max_matches=2))
    for idx in range(4):
        g.record_failure(
            f"sess-{idx}",
            f"API parser bug {idx}",
            "Parser failed on missing payload",
            files=[f"src/api_{idx}.py"],
        )
    matches = g.find_similar("parser failed missing payload", ["src/none.py"], max_matches=2)
    assert len(matches) == 2


def test_file_overlap_can_drive_match_when_keywords_do_not(store) -> None:
    g = Graveyard(
        store,
        GraveyardConfig(similarity_threshold=0.2, min_keyword_overlap=0),
    )
    g.record_failure("sess-1", "Offset pagination", "Performance cliff past 10k rows", files=["src/db/query.py"])
    matches = g.find_similar("unrelated words", ["src/db/query.py"])
    assert matches
    assert matches[0].file_overlap == ["src/db/query.py"]


def test_semantic_normalization_catches_conceptual_repeat(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.2))
    g.record_failure(
        "sess-1",
        "Redis timeout connection",
        "Cache layer failed under peak load",
        files=["src/cache.py"],
    )

    matches = g.find_similar("cache latency failure", ["src/other.py"])
    assert matches
    assert matches[0].summary == "Redis timeout connection"
    assert matches[0].semantic_score > 0.0


def test_fts_unavailable_falls_back_to_full_scan(store, monkeypatch) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.2))
    g.record_failure("sess-1", "Virtualized member list", "Sticky header regression", files=["src/list.tsx"])
    g.record_failure("sess-2", "Payment retries", "Idempotency mismatch", files=["src/payments.ts"])

    monkeypatch.setattr(SQLiteStore, "list_graveyard_fts_candidates", lambda self, **_kwargs: None)

    matches = g.find_similar("member list sticky header", ["src/list.tsx"])
    assert matches
    assert matches[0].summary == "Virtualized member list"


def test_fts_candidate_narrowing_keeps_top_match(store, monkeypatch) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.2))
    g.record_failure("sess-1", "Virtualized member list", "Sticky header regression", files=["src/list.tsx"])
    g.record_failure("sess-2", "Virtualized list", "Scroll snapping bug", files=["src/list.tsx"])
    g.record_failure("sess-3", "Cache warming", "Timeout under load", files=["src/cache.py"])

    baseline = g.find_similar("virtualized list sticky regression", ["src/list.tsx"])
    assert baseline

    all_entries = store.list_graveyard(limit=10)
    top_id = baseline[0].entry_id
    top_entry = next(entry for entry in all_entries if entry["id"] == top_id)
    narrowed = [top_entry]
    monkeypatch.setattr(SQLiteStore, "list_graveyard_fts_candidates", lambda self, **_kwargs: narrowed)
    narrowed_matches = g.find_similar("virtualized list sticky regression", ["src/list.tsx"])

    assert narrowed_matches
    assert narrowed_matches[0].entry_id == baseline[0].entry_id


def test_empty_query_and_files_returns_empty(store) -> None:
    g = Graveyard(store, GraveyardConfig())
    g.record_failure("sess-1", "Any summary", "Any reason", files=["src/a.py"])
    assert g.find_similar("", []) == []


def test_max_matches_order_is_deterministic_on_ties(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.0, max_matches=2, min_keyword_overlap=0))
    g.record_failure("sess-1", "Same words", "same words", files=["src/a.py"])
    g.record_failure("sess-2", "Same words", "same words", files=["src/b.py"])
    g.record_failure("sess-3", "Same words", "same words", files=["src/c.py"])

    first = g.find_similar("same words", ["src/z.py"])
    second = g.find_similar("same words", ["src/z.py"])

    assert [m.entry_id for m in first] == [m.entry_id for m in second]
    assert len(first) == 2


def test_semantic_score_can_bypass_min_keyword_overlap_gate(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.2, min_keyword_overlap=3))
    g.record_failure("sess-1", "Queue timeout", "worker stalled", files=["src/queue.py"])

    matches = g.find_similar("queue timeout", [])
    assert matches
    assert len(matches[0].keyword_overlap) < 3
    assert matches[0].semantic_score > 0.2


def test_tfidf_benchmark_improves_top1_vs_legacy_overlap(store) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.0, min_keyword_overlap=1, max_matches=10))
    for idx, (summary, reason) in enumerate(
        [
            ("Idempotency replay", "Payment write mismatch"),
            ("Regression dashboard", "Layout drift in chart"),
            ("Regression parser", "Input drift"),
            ("Regression cache", "Retry drift"),
            ("Redis timeout connection", "Cache layer failed under peak load"),
        ]
    ):
        g.record_failure(f"sess-{idx}", summary, reason)

    entries = store.list_graveyard(limit=200)
    cases = [
        ("regression idempotency", "Idempotency replay"),
        ("cache latency failure", "Redis timeout connection"),
        ("parser regression input", "Regression parser"),
    ]

    def legacy_ranked_summaries(query: str) -> list[str]:
        query_keywords = g._keywords(query)
        query_tokens = set(g._tokenize(query))
        scored = []
        for entry in entries:
            entry_keywords = {str(v) for v in entry.get("keywords", [])}
            entry_tokens = set(g._tokenize(f"{entry['summary']} {entry['reason']}"))
            keyword_score = len(query_keywords & entry_keywords) / max(1, len(query_keywords))
            semantic_score = g._token_jaccard(query_tokens, entry_tokens)
            scored.append((keyword_score * 0.45 + semantic_score * 0.30, int(entry["id"]), str(entry["summary"])))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [summary for _, _, summary in scored]

    new_top1 = sum(1 for query, expected in cases if g.find_similar(query, max_matches=3)[0].summary == expected)
    new_top3 = sum(
        1 for query, expected in cases if expected in [match.summary for match in g.find_similar(query, max_matches=3)]
    )
    old_top1 = sum(1 for query, expected in cases if legacy_ranked_summaries(query)[:1] == [expected])
    old_top3 = sum(1 for query, expected in cases if expected in legacy_ranked_summaries(query)[:3])

    assert new_top1 > old_top1
    assert new_top3 >= old_top3


def test_tfidf_idf_uses_stable_corpus_not_fts_candidate_subset(store, monkeypatch) -> None:
    g = Graveyard(store, GraveyardConfig(similarity_threshold=0.0, min_keyword_overlap=1, max_matches=10))
    for idx, (summary, reason) in enumerate(
        [
            ("Idempotency replay", "Payment write mismatch"),
            ("Regression dashboard", "Layout drift in chart"),
            ("Regression parser", "Input drift"),
            ("Regression cache", "Retry drift"),
            ("Redis timeout connection", "Cache layer failed under peak load"),
        ]
    ):
        g.record_failure(f"sess-{idx}", summary, reason)

    full = g.find_similar("regression idempotency", max_matches=3)
    assert full

    all_entries = store.list_graveyard(limit=200)
    top_entry = next(entry for entry in all_entries if entry["summary"] == "Idempotency replay")
    monkeypatch.setattr(SQLiteStore, "list_graveyard_fts_candidates", lambda self, **_kwargs: [top_entry])

    narrowed = g.find_similar("regression idempotency", max_matches=3)
    assert narrowed
    assert narrowed[0].summary == "Idempotency replay"
    assert abs(narrowed[0].score - full[0].score) < 1e-9
