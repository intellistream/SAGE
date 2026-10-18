from sage.runtime.evidence_relevance import subject_candidate_indices


def test_collection_label_does_not_promote_unrelated_documents():
    assert subject_candidate_indices(
        ("Wiki", "StateAxis"),
        (
            "Wiki | StateAxis limitations",
            "Wiki | prompt tutorial",
            "Wiki | a handbook",
        ),
    ) == (0,)


def test_all_comparison_subjects_and_late_mentions_are_preserved():
    assert subject_candidate_indices(
        ("Library", "Alpha", "Beta"),
        (
            "Library " + "text " * 1000 + "Alpha",
            "Library Beta",
            "Library unrelated",
        ),
    ) == (0, 1)


def test_no_discriminating_match_preserves_semantic_candidates():
    assert subject_candidate_indices(("Wiki", "unknown"), ("Wiki a", "Wiki b")) == (0, 1)
    assert subject_candidate_indices((), ("a", "b")) == (0, 1)
    assert subject_candidate_indices(("Alpha",), ("Alpha only",)) == (0,)


def test_subject_is_literal_and_not_substring():
    assert subject_candidate_indices(("Alpha",), ("Alphanumeric", "Alpha")) == (1,)
    assert subject_candidate_indices(("A+B",), ("AAB", "A+B")) == (1,)
