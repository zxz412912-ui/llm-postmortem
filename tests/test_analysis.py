from llm_postmortem.analysis import analyze, classify, is_failure
from llm_postmortem.report import render_markdown


def test_failure_detection_and_classification():
    record = {"status": "failed", "response": "JSON parse error", "feedback": "schema validation"}
    assert is_failure(record)
    assert classify(record) == "format_error"


def test_report_contains_actionable_findings():
    report = analyze([
        {"trace_id": "a", "model": "small", "status": "failed", "feedback": "hallucinated made up facts"},
        {"trace_id": "b", "model": "small", "status": "success", "score": 1},
    ])
    rendered = render_markdown(report)
    assert report.failed_calls == 1
    assert "Hallucination" in rendered
    assert "Model health" in rendered


def test_retrieval_signal_beats_generic_cant_response():
    record = {"status": "failed", "response": "I can't find a relevant document", "feedback": "Retrieval returned no documents"}
    assert classify(record) == "retrieval_failure"
