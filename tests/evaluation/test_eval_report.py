"""Unit tests for the pure triage logic in scripts/eval_report.py (synthetic data only)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from mlflow.entities import Feedback  # noqa: E402

import eval_report as er  # noqa: E402
from eval_report import Case, Verdict  # noqa: E402


def _case(case_id: str = "full_001", agent: str = "faq", **statuses: str) -> Case:
    return Case(
        case_id=case_id,
        trace_id=f"tr-{case_id}",
        agent=agent,
        request="hello",
        verdicts={name: Verdict(status, f"{name} said {status}") for name, status in statuses.items()},
    )


# --- verdict normalisation --------------------------------------------------
def test_yes_no_strings_and_bools_are_normalised():
    assert er.verdict_from_feedback(Feedback(name="correctness", value="no")).status == er.FAIL
    assert er.verdict_from_feedback(Feedback(name="correctness", value="yes")).status == er.PASS
    assert er.verdict_from_feedback(Feedback(name="intention_routing", value=False)).status == er.FAIL
    assert er.verdict_from_feedback(Feedback(name="intention_routing", value=True)).status == er.PASS


def test_none_value_is_not_applicable_and_error_is_not_a_failure():
    assert er.verdict_from_feedback(Feedback(name="x", value=None)) is None
    assert er.verdict_from_feedback(Feedback(name="x", error="boom")).status == er.ERROR


def test_unrecognised_value_is_flagged_not_guessed():
    assert er.verdict_from_feedback(Feedback(name="x", value="pass")).status == er.UNKNOWN


def test_metadata_is_preserved():
    fb = Feedback(name="intention_routing", value=False, metadata={"expected": "faq", "actual": "booking"})
    assert er.verdict_from_feedback(fb).metadata == {"expected": "faq", "actual": "booking"}


# --- classification ---------------------------------------------------------
def test_clean_case():
    t = er.classify(_case(correctness="pass", intention_routing="pass"))
    assert (t.root_cause, t.priority, t.is_failure) == ("NONE", "NONE", False)


def test_routing_is_root_cause_and_downstream_failures_cascade():
    t = er.classify(
        _case(intention_routing="fail", correctness="fail", tool_call_correctness="fail", relevance_to_query="fail")
    )
    assert (t.root_cause, t.priority) == ("ROUTING", "HIGH")
    assert t.also_failed == ["tool_call_correctness", "correctness", "relevance_to_query"]


def test_priority_by_stage():
    assert er.classify(_case(tool_call_correctness="fail")).priority == "HIGH"
    assert er.classify(_case(correctness="fail")).priority == "MEDIUM"
    assert er.classify(_case(tool_call_efficiency="fail")).priority == "LOW"


def test_scorer_error_is_never_an_agent_failure():
    t = er.classify(_case(correctness="error", intention_routing="pass"))
    assert (t.root_cause, t.priority, t.is_failure) == ("SCORER_ERROR", "UNVERIFIED", False)


def test_failure_plus_error_keeps_failure_root_cause():
    t = er.classify(_case(intention_routing="fail", tool_call_efficiency="error"))
    assert t.root_cause == "ROUTING" and t.unverified == ["tool_call_efficiency"]


def test_agent_error_outranks_everything():
    case = _case(intention_routing="fail")
    case.agent_error = True
    t = er.classify(case)
    assert (t.root_cause, t.priority) == ("AGENT_ERROR", "HIGH")


def test_unknown_scorer_failure_is_reported_as_other():
    t = er.classify(_case(my_new_scorer="fail"))
    assert (t.root_cause, t.priority) == ("OTHER", "MEDIUM")


def test_judge_suspect_requires_all_other_signals_passing():
    suspect = _case(
        correctness="fail", intention_routing="pass", tool_call_correctness="pass", relevance_to_query="pass"
    )
    assert er.classify(suspect).judge_suspect is True
    # Missing signal (e.g. sanity dataset) -> cannot conclude.
    assert er.classify(_case(correctness="fail", intention_routing="pass")).judge_suspect is False
    # Relevance also failing -> not a lone judge complaint.
    assert er.classify(_case(
        correctness="fail", intention_routing="pass", tool_call_correctness="pass", relevance_to_query="fail"
    )).judge_suspect is False


# --- stats / selection ------------------------------------------------------
def test_scorer_stats_and_pass_rate():
    cases = [
        _case("a", correctness="pass"),
        _case("b", correctness="fail"),
        _case("c", correctness="error"),
        _case("d", intention_routing="pass"),
    ]
    stat = er.scorer_stats(cases)["correctness"]
    assert stat == {er.PASS: 1, er.FAIL: 1, "unverified": 1, "n/a": 1}
    assert er.pass_rate(stat) == 0.5


def test_representatives_prefer_distinct_agents_and_respect_cap():
    cases = [_case(f"c{i}", agent=a, intention_routing="fail") for i, a in enumerate(["faq", "faq", "faq", "booking"])]
    triages = [er.classify(c) for c in cases]
    picked = er.select_representatives(cases, triages, per_cause=2)
    assert len(picked) == 2
    assert {c.agent for c, _ in picked} == {"faq", "booking"}


def test_priorities_sort_by_severity_not_alphabetically():
    ordered = sorted(["LOW", "HIGH", "MEDIUM"], key=er.PRIORITY_RANK.get)
    assert ordered == ["HIGH", "MEDIUM", "LOW"]


# --- rendering --------------------------------------------------------------
def _analysis(cases: list[Case]) -> er.Analysis:
    meta = er.RunMeta("run1", "eval-run", "1", "2026-01-01 00:00", "`prompt-eval-v3`", "gemini")
    return er.Analysis(meta, cases, [er.classify(c) for c in cases])


def test_report_renders_core_sections_and_baseline_diff():
    routing_fail = _case("full_002", agent="faq", intention_routing="fail", correctness="fail")
    routing_fail.verdicts["intention_routing"].metadata = {"expected": "faq", "actual": "booking"}
    current = _analysis([_case("full_001", correctness="pass"), routing_fail])
    baseline = _analysis([_case("full_001", correctness="fail"), _case("full_002", agent="faq", correctness="pass")])

    report = er.render_report(current, per_cause=3, baseline=baseline)

    assert "## Verdict" in report and "1 failed" in report
    assert "ROUTING" in report and "Routing confusion" in report
    assert "| faq | booking | 1 |" in report
    assert "1 regressions" in report and "1 fixes" in report
    assert "tag.`triage.priority` = 'HIGH'" in report


def test_cases_dataframe_is_sorted_by_priority():
    cases = [_case("a", tool_call_efficiency="fail"), _case("b", intention_routing="fail"), _case("c", correctness="pass")]
    df = er.cases_dataframe(_analysis(cases))
    assert list(df["case_id"]) == ["b", "a", "c"]
