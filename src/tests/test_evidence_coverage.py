import json
from dataclasses import replace

import pytest

from sage.runtime.evidence_coverage import (
    EvidenceRequirement,
    InvalidEvidenceCoverage,
    coverage_response_format,
    prepare_coverage,
    question_requirements,
    repair_queries,
    validate_coverage,
)
from sage.runtime.source_answer_plan import PlanSource


def request():
    return prepare_coverage("A? B?", (EvidenceRequirement("a", 0, 3), EvidenceRequirement("b", 3, 5)),
        (PlanSource("public", "A", "https://example.org/a", "A uses state ownership. Measurements are not displayed here."),))


def response(req, **changes):
    data = {"digest": req.digest, "items": [
        {"requirement_id": "a", "witnesses": [{"source_id": "public", "start_line": 1, "end_line": 1}]},
        {"requirement_id": "b", "witnesses": []}]}
    data.update(changes)
    return json.dumps(data)


def test_complete_question_and_exact_witnesses_bind_repair():
    req = request()
    checked = validate_coverage(req, response(req))
    assert checked.missing_ids == ("b",)
    assert repair_queries(req, checked) == ("B?",)
    assert "Measurements are not displayed here." in req.payload
    assert coverage_response_format(req)["json_schema"]["strict"] is True


@pytest.mark.parametrize("start,end", [(0, 1), (1, 2), (2, 1), (True, 1), (1, 1.0), ("1", 1)])
def test_witness_ranges_fail_closed(start, end):
    req = request()
    with pytest.raises(InvalidEvidenceCoverage):
        validate_coverage(req, response(req, items=[{"requirement_id": "a", "witnesses": [
            {"source_id": "public", "start_line": start, "end_line": end}]},
            {"requirement_id": "b", "witnesses": []}]))


def test_source_lines_are_lossless_and_receipts_cannot_replace_source_text():
    req = request()
    content = "标题\r\n\r\n测量数据未在本文展示。\n完整链接：https://example.org/full?q=one&n=two"
    req = prepare_coverage(req.question, req.requirements, (replace(req.sources[0], content=content),))
    payload = json.loads(req.payload)
    assert "".join(line["text"] for line in payload["sources"][0]["lines"]) == content
    checked = validate_coverage(req, response(req, items=[{"requirement_id": "a", "witnesses": [
        {"source_id": "public", "start_line": 3, "end_line": 4}]},
        {"requirement_id": "b", "witnesses": []}]))
    assert checked.items[0].witnesses[0].quote == "".join(content.splitlines(keepends=True)[2:])
    tampered = replace(checked, items=(replace(checked.items[0], witnesses=(
        replace(checked.items[0].witnesses[0], quote="作者从未测量"),)), checked.items[1]))
    with pytest.raises(InvalidEvidenceCoverage, match="receipt content changed"):
        repair_queries(req, tampered)


@pytest.mark.parametrize("requirements", [(), (EvidenceRequirement("a", 1, 5),),
    (EvidenceRequirement("a", 0, 4),), (EvidenceRequirement("a", 0, 3), EvidenceRequirement("a", 3, 5)),
    (EvidenceRequirement("a", 0, 3), EvidenceRequirement("b", 2, 5)),
    (EvidenceRequirement("a", False, 5),)])
def test_partition_cannot_silently_drop_rewrite_or_duplicate_question(requirements):
    with pytest.raises(InvalidEvidenceCoverage):
        prepare_coverage("A? B?", requirements, request().sources)


@pytest.mark.parametrize("source,quote", [("private-not-authorized", "A uses state ownership."),
    ("public", "No measurements were ever performed."), ("public", ""), ("public", " "),
    ("public", None), ([], "A")])
def test_unwitnessed_claim_cannot_become_a_coverage_receipt(source, quote):
    req = request()
    with pytest.raises(InvalidEvidenceCoverage):
        validate_coverage(req, response(req, items=[{"requirement_id": "a", "witnesses": [
            {"source_id": source, "quote": quote}]}, {"requirement_id": "b", "witnesses": []}]))


@pytest.mark.parametrize("items", [[], [{"requirement_id": "a", "witnesses": []}],
    [{"requirement_id": "a", "witnesses": []}]*2,
    [{"requirement_id": "unknown", "witnesses": []}],
    [{"requirement_id": "a", "witnesses": [], "passed": True}]])
def test_no_missing_duplicate_unknown_or_model_passed_flags(items):
    with pytest.raises(InvalidEvidenceCoverage):
        validate_coverage(request(), response(request(), items=items))


def test_changed_question_sources_or_requirements_require_a_fresh_assessment():
    req = request()
    checked = validate_coverage(req, response(req))
    for changed in [prepare_coverage("C? B?", req.requirements, req.sources),
                    prepare_coverage(req.question, req.requirements,
                        (replace(req.sources[0], content=req.sources[0].content+" More context."),))]:
        with pytest.raises(InvalidEvidenceCoverage):
            repair_queries(changed, checked)
    with pytest.raises(InvalidEvidenceCoverage):
        validate_coverage(req, response(req).replace('"digest":', '"digest":"duplicate", "digest":'))


def test_empty_retrieval_maps_explicit_gaps_and_preserves_the_whole_question():
    req = prepare_coverage("No source?", (EvidenceRequirement("all", 0, 10),), ())
    result = validate_coverage(req, json.dumps({"digest": req.digest,
        "items": [{"requirement_id": "all", "witnesses": []}]}))
    assert repair_queries(req, result) == ("No source?",)


def test_syntactic_partition_retains_every_character_and_qualifier():
    question = "A 和 B 分别是什么？\n请给出处；不要推断没有实验。  "
    parts = question_requirements(question)
    assert len(parts) > 1
    assert "".join(question[r.start:r.end] for r in parts) == question
    prepare_coverage(question, parts, ())


@pytest.mark.parametrize("field", ["question", "sources", "requirements", "payload"])
def test_request_cannot_be_rebound_while_reusing_the_digest(field):
    req = request()
    replacements = {"question": "C? B?", "sources": (replace(req.sources[0], content="changed"),),
        "requirements": (EvidenceRequirement("all", 0, 5),), "payload": req.payload+" "}
    with pytest.raises(InvalidEvidenceCoverage):
        validate_coverage(replace(req, **{field: replacements[field]}), response(req))
