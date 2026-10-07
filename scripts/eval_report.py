"""
Auto-triage report for MLflow evaluation runs.

Turns the raw "traces x scorers" matrix of a `mlflow.genai.evaluate()` run into a
short, prioritised list of traces worth opening, and writes the findings back to
MLflow so the trace UI can be filtered instead of scrolled.

Data source (MLflow-native, zero LLM calls):
    mlflow.search_traces(run_id=...)  ->  TraceInfo.assessments (Feedback from scorers)
                                          TraceInfo.tags (dataset record tags:
                                          `index`, `agent_under_test`)

Failure model (causal pipeline order, first failing stage = root cause):
    AGENT_ERROR      trace state ERROR (agent raised)                    HIGH
    ROUTING          intention_routing        == fail                    HIGH
    TOOL_USE         tool_call_correctness    == no                      HIGH
    CONTENT          correctness              == no                      MEDIUM
    RELEVANCE        relevance_to_query       == no                      MEDIUM
    TOOL_EFFICIENCY  tool_call_efficiency     == no                      LOW
    SCORER_ERROR     a scorer crashed / returned an unrecognised value   UNVERIFIED
Later failures in the same case are reported as "also failed" (cascade).

`judge_suspect`: correctness failed although intention_routing and
tool_call_correctness passed and relevance_to_query is "yes" -> the evaluator or
the dataset's expected_facts deserve a look before blaming the agent.

Write-back (additive only, skipped with --no-write):
    trace tags : triage.root_cause, triage.priority, triage.judge_suspect
    run files  : triage/report.md, triage/cases.csv
    run metrics: triage/failed_cases, triage/high_priority_cases,
                 triage/judge_suspect_cases, triage/unverified_cases, triage/pass_rate

Usage (user-run; reads results only, never calls scorers or the agent):
    uv run python scripts/eval_report.py --latest
    uv run python scripts/eval_report.py --run-id <run_id>
    uv run python scripts/eval_report.py --run-id <run_id> --baseline <older_run_id>
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

import mlflow
from mlflow import MlflowClient
from mlflow.entities import Feedback, Trace
from mlflow.entities.trace_state import TraceState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Failure model
# ---------------------------------------------------------------------------
PASS, FAIL, ERROR, UNKNOWN = "pass", "fail", "error", "unknown"

PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNVERIFIED": 3, "NONE": 4}
FAILURE_PRIORITIES = ("HIGH", "MEDIUM", "LOW")


@dataclass(frozen=True)
class Stage:
    """One scorer in the causal pipeline and the failure it represents."""

    scorer: str
    root_cause: str
    priority: str


# Order = causal order of the LangGraph pipeline (coordinator -> tools -> response).
# Names are the real scorer names registered in scripts/scorers.py.
STAGES: tuple[Stage, ...] = (
    Stage("intention_routing", "ROUTING", "HIGH"),
    Stage("tool_call_correctness", "TOOL_USE", "HIGH"),
    Stage("correctness", "CONTENT", "MEDIUM"),
    Stage("relevance_to_query", "RELEVANCE", "MEDIUM"),
    Stage("tool_call_efficiency", "TOOL_EFFICIENCY", "LOW"),
)
CAUSE_ORDER = (
    "AGENT_ERROR",
    *[s.root_cause for s in STAGES],
    "OTHER",
    "SCORER_ERROR",
)
KNOWN_SCORERS = {s.scorer for s in STAGES}

TAG_ROOT_CAUSE = "triage.root_cause"
TAG_PRIORITY = "triage.priority"
TAG_JUDGE_SUSPECT = "triage.judge_suspect"

REPORTS_DIR = Path(__file__).resolve().parent.parent / "evaluation" / "reports"


@dataclass
class Verdict:
    """Normalised outcome of one scorer on one trace."""

    status: str  # pass | fail | error | unknown
    rationale: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Case:
    """One evaluated trace (= one dataset record)."""

    case_id: str
    trace_id: str
    agent: str
    request: str
    verdicts: dict[str, Verdict]
    agent_error: bool = False


@dataclass
class Triage:
    root_cause: str
    priority: str
    root_scorer: str | None
    also_failed: list[str]
    unverified: list[str]
    judge_suspect: bool

    @property
    def is_failure(self) -> bool:
        return self.priority in FAILURE_PRIORITIES


# ---------------------------------------------------------------------------
# Normalisation (MLflow entities -> Case)
# ---------------------------------------------------------------------------
def verdict_from_feedback(feedback: Feedback) -> Verdict | None:
    """Normalise a scorer Feedback. Returns None when the scorer was N/A for the trace.

    LLM judges emit CategoricalRating "yes"/"no" strings, deterministic scorers emit
    bools. Comparing against `False` (as a naive implementation would) silently misses
    every "no".
    """
    if feedback.error_message is not None:
        return Verdict(ERROR, feedback.error_message)

    value = feedback.value
    rationale = feedback.rationale or ""
    metadata = dict(feedback.metadata or {})
    if value is None:
        return None
    if isinstance(value, str) and (rating := value.strip().lower()) in ("yes", "no"):
        return Verdict(PASS if rating == "yes" else FAIL, rationale, metadata)
    if pd.api.types.is_bool(value):
        return Verdict(PASS if value else FAIL, rationale, metadata)
    return Verdict(UNKNOWN, f"unrecognised value {value!r}. {rationale}".strip(), metadata)


def _request_text(trace: Trace) -> str:
    """User message of the trace (dataset input `user_message`) or the raw preview."""
    preview = trace.info.request_preview or ""
    try:
        parsed = json.loads(preview)
    except (TypeError, ValueError):
        return preview
    if isinstance(parsed, dict) and "user_message" in parsed:
        return str(parsed["user_message"])
    return preview


def case_from_trace(trace: Trace) -> Case:
    tags = trace.info.tags or {}
    # A re-scored trace carries several assessments per scorer; the newest valid one wins.
    feedbacks = sorted(
        (
            a
            for a in trace.info.assessments
            if isinstance(a, Feedback) and a.valid is not False
        ),
        key=lambda a: a.last_update_time_ms or 0,
    )
    verdicts: dict[str, Verdict] = {}
    for feedback in feedbacks:
        verdict = verdict_from_feedback(feedback)
        if verdict is None:
            verdicts.pop(feedback.name, None)
        else:
            verdicts[feedback.name] = verdict

    return Case(
        case_id=tags.get("index") or trace.info.trace_id,
        trace_id=trace.info.trace_id,
        agent=tags.get("agent_under_test", "unknown"),
        request=_request_text(trace),
        verdicts=verdicts,
        agent_error=trace.info.state == TraceState.ERROR,
    )


# ---------------------------------------------------------------------------
# Classification (pure functions)
# ---------------------------------------------------------------------------
def _stages_for(case: Case) -> list[Stage]:
    extra = sorted(n for n in case.verdicts if n not in KNOWN_SCORERS)
    return [*STAGES, *[Stage(n, "OTHER", "MEDIUM") for n in extra]]


def _status(case: Case, scorer: str) -> str | None:
    verdict = case.verdicts.get(scorer)
    return verdict.status if verdict else None


def is_judge_suspect(case: Case) -> bool:
    return (
        _status(case, "correctness") == FAIL
        and _status(case, "intention_routing") == PASS
        and _status(case, "tool_call_correctness") == PASS
        and _status(case, "relevance_to_query") == PASS
    )


def classify(case: Case) -> Triage:
    failed = [s for s in _stages_for(case) if _status(case, s.scorer) == FAIL]
    unverified = sorted(n for n, v in case.verdicts.items() if v.status in (ERROR, UNKNOWN))

    if case.agent_error:
        return Triage("AGENT_ERROR", "HIGH", None, [s.scorer for s in failed], unverified, False)
    if failed:
        root, rest = failed[0], failed[1:]
        return Triage(
            root.root_cause,
            root.priority,
            root.scorer,
            [s.scorer for s in rest],
            unverified,
            is_judge_suspect(case),
        )
    if unverified:
        return Triage("SCORER_ERROR", "UNVERIFIED", None, [], unverified, False)
    return Triage("NONE", "NONE", None, [], [], False)


def root_rationale(case: Case, triage: Triage) -> str:
    if triage.root_cause == "AGENT_ERROR":
        return "agent raised an exception (trace state ERROR)"
    if triage.root_scorer:
        return case.verdicts[triage.root_scorer].rationale
    if triage.unverified:
        return "; ".join(f"{n}: {case.verdicts[n].rationale}" for n in triage.unverified)
    return ""


def scorer_stats(cases: list[Case]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    names = sorted({n for c in cases for n in c.verdicts}, key=_scorer_sort_key)
    for name in names:
        counts = Counter(c.verdicts[name].status for c in cases if name in c.verdicts)
        stats[name] = {
            PASS: counts[PASS],
            FAIL: counts[FAIL],
            "unverified": counts[ERROR] + counts[UNKNOWN],
            "n/a": len(cases) - sum(counts.values()),
        }
    return stats


def _scorer_sort_key(name: str) -> tuple[int, str]:
    order = [s.scorer for s in STAGES]
    return (order.index(name) if name in order else len(order), name)


def pass_rate(stat: dict[str, int]) -> float | None:
    decided = stat[PASS] + stat[FAIL]
    return stat[PASS] / decided if decided else None


# ---------------------------------------------------------------------------
# Selection of traces to inspect
# ---------------------------------------------------------------------------
def select_representatives(
    cases: list[Case], triages: list[Triage], per_cause: int
) -> list[tuple[Case, Triage]]:
    """Up to `per_cause` cases per root cause, preferring distinct agents_under_test."""
    by_cause: dict[str, list[tuple[Case, Triage]]] = defaultdict(list)
    for case, triage in zip(cases, triages):
        if triage.is_failure:
            by_cause[triage.root_cause].append((case, triage))

    selected: list[tuple[Case, Triage]] = []
    for cause in CAUSE_ORDER:
        pool = by_cause.get(cause, [])
        pool.sort(key=lambda ct: (-len(ct[1].also_failed), ct[0].case_id))
        chosen: list[tuple[Case, Triage]] = []
        seen_agents: set[str] = set()
        for item in pool:  # first pass: one per agent
            if len(chosen) < per_cause and item[0].agent not in seen_agents:
                chosen.append(item)
                seen_agents.add(item[0].agent)
        for item in pool:  # second pass: fill remaining slots
            if len(chosen) < per_cause and item not in chosen:
                chosen.append(item)
        selected.extend(chosen)
    return selected


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def _cell(text: Any, limit: int = 110) -> str:
    s = " ".join(str(text if text is not None else "").split()).replace("|", "\\|")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_cell(c, 140) for c in row) + " |" for row in rows]
    return lines + [""]


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


@dataclass
class RunMeta:
    run_id: str
    name: str
    experiment_id: str
    started: str
    dataset: str
    model_tag: str


@dataclass
class Analysis:
    meta: RunMeta
    cases: list[Case]
    triages: list[Triage]

    @property
    def failures(self) -> list[tuple[Case, Triage]]:
        return [(c, t) for c, t in zip(self.cases, self.triages) if t.is_failure]

    def counts(self) -> dict[str, int]:
        total = len(self.cases)
        failed = len(self.failures)
        return {
            "total": total,
            "failed": failed,
            "passed": sum(1 for t in self.triages if t.priority == "NONE"),
            "high": sum(1 for t in self.triages if t.priority == "HIGH"),
            "medium": sum(1 for t in self.triages if t.priority == "MEDIUM"),
            "low": sum(1 for t in self.triages if t.priority == "LOW"),
            "suspect": sum(1 for t in self.triages if t.judge_suspect),
            "unverified": sum(1 for t in self.triages if t.unverified),
        }


def render_report(analysis: Analysis, per_cause: int, baseline: Analysis | None) -> str:
    meta, cases, triages = analysis.meta, analysis.cases, analysis.triages
    n = analysis.counts()
    stats = scorer_stats(cases)
    base_stats = scorer_stats(baseline.cases) if baseline else {}
    out: list[str] = ["# Evaluation Triage Report", ""]

    out += [
        f"- **Run:** `{meta.name}` (`{meta.run_id}`) · experiment `{meta.experiment_id}` · {meta.started}",
        f"- **Dataset:** {meta.dataset} · **Agent model:** {meta.model_tag}",
        f"- **Generated:** {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "## Verdict",
        "",
        (
            f"**{n['total']} cases · {n['passed']} clean ({_pct(n['passed'] / n['total'] if n['total'] else None)}) · "
            f"{n['failed']} failed ({n['high']} HIGH / {n['medium']} MEDIUM / {n['low']} LOW) · "
            f"{n['suspect']} judge-suspect · {n['unverified']} with scorer errors**"
        ),
        "",
    ]

    # Scorer pass rates
    out += ["## Scorer pass rates", ""]
    rows = []
    for name, stat in stats.items():
        row = [f"`{name}`", _pct(pass_rate(stat)), stat[PASS], stat[FAIL], stat["unverified"], stat["n/a"]]
        if baseline:
            base = base_stats.get(name)
            if base and pass_rate(base) is not None and pass_rate(stat) is not None:
                row.append(f"{(pass_rate(stat) - pass_rate(base)) * 100:+.0f} pp")
            else:
                row.append("n/a")
        rows.append(row)
    headers = ["Scorer", "Pass rate", "Pass", "Fail", "Scorer errors", "N/A"]
    if baseline:
        headers.append("Δ vs baseline")
    out += _table(headers, rows)
    unclassified = sorted(set(stats) - KNOWN_SCORERS)
    if unclassified:
        out += [f"> Scorers not in the triage model (reported as root cause `OTHER`): {', '.join(unclassified)}", ""]

    # Root causes
    out += ["## Root causes", ""]
    if analysis.failures:
        cause_rows = []
        for cause in CAUSE_ORDER:
            group = [(c, t) for c, t in analysis.failures if t.root_cause == cause]
            if group:
                cascade = sum(len(t.also_failed) for _, t in group)
                cause_rows.append([cause, group[0][1].priority, len(group), cascade])
        out += _table(["Root cause", "Priority", "Cases", "Downstream failures (cascade)"], cause_rows)

        # By agent
        out += ["## Failures by agent under test", ""]
        causes_present = [c for c in CAUSE_ORDER if any(t.root_cause == c for _, t in analysis.failures)]
        agent_rows = []
        for agent in sorted({c.agent for c in cases}):
            agent_cases = [(c, t) for c, t in zip(cases, triages) if c.agent == agent]
            agent_rows.append(
                [agent, len(agent_cases), sum(1 for _, t in agent_cases if t.is_failure)]
                + [sum(1 for _, t in agent_cases if t.root_cause == cause) for cause in causes_present]
            )
        out += _table(["Agent", "Cases", "Failed", *causes_present], agent_rows)
    else:
        out += ["No agent failures detected.", ""]

    # Routing confusion
    routing = Counter()
    for case, triage in zip(cases, triages):
        verdict = case.verdicts.get("intention_routing")
        if verdict and verdict.status == FAIL:
            routing[(verdict.metadata.get("expected", "?"), verdict.metadata.get("actual", "?"))] += 1
    if routing:
        out += ["## Routing confusion (intention_routing failures)", ""]
        out += _table(
            ["Expected", "Actual", "Cases"],
            [[e, a, c] for (e, a), c in routing.most_common()],
        )

    # Inspect first
    selected = select_representatives(cases, triages, per_cause)
    out += [f"## Inspect first ({len(selected)} of {len(analysis.failures)} failing traces)", ""]
    if selected:
        out += ["Representative traces per root cause, distinct agents first. Full list: `triage/cases.csv`.", ""]
        out += _table(
            ["Case", "Agent", "Root cause", "Request", "Why", "Also failed", "Trace ID"],
            [
                [
                    c.case_id,
                    c.agent,
                    f"{t.root_cause} ({t.priority})",
                    c.request,
                    root_rationale(c, t),
                    ", ".join(t.also_failed) or "-",
                    f"`{c.trace_id}`",
                ]
                for c, t in selected
            ],
        )
    else:
        out += ["Nothing to inspect.", ""]

    # Judge suspects
    suspects = [(c, t) for c, t in zip(cases, triages) if t.judge_suspect]
    if suspects:
        out += [
            f"## Judge / dataset suspects ({len(suspects)})",
            "",
            "Routing and tools passed and the answer is relevant, yet `correctness` failed. "
            "Check the case's `expected_facts` and the judge rationale before changing a prompt.",
            "",
        ]
        out += _table(
            ["Case", "Agent", "Request", "Correctness rationale", "Trace ID"],
            [
                [c.case_id, c.agent, c.request, c.verdicts["correctness"].rationale, f"`{c.trace_id}`"]
                for c, _ in suspects
            ],
        )

    # Scorer errors
    errored = [(c, t) for c, t in zip(cases, triages) if t.unverified]
    if errored:
        out += [
            f"## Scorer errors ({len(errored)} cases)",
            "",
            "A scorer crashed or returned an unrecognised value. These are evaluator problems, "
            "not agent failures.",
            "",
        ]
        out += _table(
            ["Case", "Scorer(s)", "Detail", "Trace ID"],
            [
                [c.case_id, ", ".join(t.unverified), "; ".join(c.verdicts[s].rationale for s in t.unverified), f"`{c.trace_id}`"]
                for c, t in errored
            ],
        )

    # Baseline diff
    if baseline:
        out += render_baseline_diff(analysis, baseline)

    out += [
        "## Open them in the MLflow UI",
        "",
        "Trace tags were written by this report. In the experiment's **Traces** tab, filter with:",
        "",
        "```",
        "tag.`triage.priority` = 'HIGH'",
        "tag.`triage.root_cause` = 'ROUTING'",
        "tag.`triage.judge_suspect` = 'true'",
        "```",
        "",
        "For problems no scorer covers, run MLflow's *Automatic Issue Detection* from the Traces tab "
        "(LLM-clustered issues, CLEARS categories).",
        "",
    ]
    return "\n".join(out)


def render_baseline_diff(current: Analysis, baseline: Analysis) -> list[str]:
    cur = {c.case_id: (c, t) for c, t in zip(current.cases, current.triages)}
    base = {c.case_id: (c, t) for c, t in zip(baseline.cases, baseline.triages)}
    shared = sorted(set(cur) & set(base))

    regressions = [i for i in shared if cur[i][1].is_failure and not base[i][1].is_failure]
    fixes = [i for i in shared if base[i][1].is_failure and not cur[i][1].is_failure]
    still_failing = [i for i in shared if cur[i][1].is_failure and base[i][1].is_failure]

    out = [
        f"## Changes vs baseline `{baseline.meta.name}` (`{baseline.meta.run_id}`)",
        "",
        f"{len(shared)} matching cases · **{len(regressions)} regressions** · "
        f"**{len(fixes)} fixes** · {len(still_failing)} still failing · "
        f"{len(set(cur) - set(base))} new · {len(set(base) - set(cur))} missing",
        "",
    ]
    if regressions:
        out += ["### Regressions (passed before, fail now)", ""]
        out += _table(
            ["Case", "Agent", "Now fails as", "Why"],
            [
                [i, cur[i][0].agent, cur[i][1].root_cause, root_rationale(*cur[i])]
                for i in regressions
            ],
        )
    if fixes:
        out += ["### Fixes (failed before, pass now)", ""]
        out += _table(
            ["Case", "Agent", "Failed before as"],
            [[i, base[i][0].agent, base[i][1].root_cause] for i in fixes],
        )
    return out


def cases_dataframe(analysis: Analysis) -> pd.DataFrame:
    scorer_names = sorted({n for c in analysis.cases for n in c.verdicts}, key=_scorer_sort_key)
    rows = []
    for case, triage in zip(analysis.cases, analysis.triages):
        row: dict[str, Any] = {
            "case_id": case.case_id,
            "agent": case.agent,
            "priority": triage.priority,
            "root_cause": triage.root_cause,
            "judge_suspect": triage.judge_suspect,
            "root_scorer": triage.root_scorer or "",
            "also_failed": ",".join(triage.also_failed),
            "why": root_rationale(case, triage),
            "request": case.request,
            "trace_id": case.trace_id,
        }
        for name in scorer_names:
            row[name] = case.verdicts[name].status if name in case.verdicts else "n/a"
        rows.append(row)
    df = pd.DataFrame(rows)
    df["_rank"] = df["priority"].map(PRIORITY_RANK)
    return df.sort_values(["_rank", "root_cause", "case_id"]).drop(columns="_rank")


# ---------------------------------------------------------------------------
# MLflow I/O
# ---------------------------------------------------------------------------
def load_analysis(client: MlflowClient, run_id: str) -> Analysis:
    run = client.get_run(run_id)
    traces = mlflow.search_traces(
        locations=[run.info.experiment_id],
        run_id=run_id,
        include_spans=False,
        return_type="list",
    )
    if not traces:
        raise SystemExit(f"No traces are linked to run '{run_id}'. Is it an evaluation run?")

    datasets = run.inputs.dataset_inputs
    meta = RunMeta(
        run_id=run_id,
        name=run.info.run_name or run_id,
        experiment_id=run.info.experiment_id,
        started=datetime.fromtimestamp(run.info.start_time / 1000).strftime("%Y-%m-%d %H:%M"),
        dataset=f"`{datasets[0].dataset.name}`" if datasets else "unknown",
        model_tag=run.data.tags.get("llm_model_id", "unknown"),
    )
    cases = sorted((case_from_trace(t) for t in traces), key=lambda c: c.case_id)
    return Analysis(meta, cases, [classify(c) for c in cases])


def latest_evaluation_run_id(client: MlflowClient, experiment_id: str) -> str:
    """Most recent run that has traces linked to it (i.e. an evaluation run)."""
    runs = client.search_runs(
        [experiment_id], order_by=["attributes.start_time DESC"], max_results=20
    )
    for run in runs:
        linked = mlflow.search_traces(
            locations=[experiment_id],
            run_id=run.info.run_id,
            include_spans=False,
            max_results=1,
            return_type="list",
        )
        if linked:
            return run.info.run_id
    raise SystemExit(f"No evaluation run with linked traces found in experiment '{experiment_id}'.")


def write_back(client: MlflowClient, analysis: Analysis, report: str) -> None:
    run_id = analysis.meta.run_id
    for case, triage in zip(analysis.cases, analysis.triages):
        client.set_trace_tag(case.trace_id, TAG_ROOT_CAUSE, triage.root_cause)
        client.set_trace_tag(case.trace_id, TAG_PRIORITY, triage.priority)
        client.set_trace_tag(case.trace_id, TAG_JUDGE_SUSPECT, str(triage.judge_suspect).lower())

    client.log_text(run_id, report, "triage/report.md")
    client.log_text(run_id, cases_dataframe(analysis).to_csv(index=False), "triage/cases.csv")

    n = analysis.counts()
    metrics = {
        "triage/failed_cases": n["failed"],
        "triage/high_priority_cases": n["high"],
        "triage/judge_suspect_cases": n["suspect"],
        "triage/unverified_cases": n["unverified"],
        "triage/pass_rate": n["passed"] / n["total"] if n["total"] else 0.0,
    }
    for key, value in metrics.items():
        client.log_metric(run_id, key, value)


def generate_report(
    run_id: str,
    baseline_run_id: str | None = None,
    write_to_mlflow: bool = True,
    per_cause: int = 3,
) -> Path:
    """Build the triage report for `run_id`; returns the local markdown path."""
    client = MlflowClient()
    analysis = load_analysis(client, run_id)
    baseline = load_analysis(client, baseline_run_id) if baseline_run_id else None
    report = render_report(analysis, per_cause, baseline)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{run_id}.md"
    path.write_text(report, encoding="utf-8")

    if write_to_mlflow:
        write_back(client, analysis, report)

    n = analysis.counts()
    print("=" * 60)
    print("Evaluation triage")
    print(
        f"  {n['total']} cases · {n['passed']} clean · {n['failed']} failed "
        f"({n['high']} HIGH / {n['medium']} MEDIUM / {n['low']} LOW) · "
        f"{n['suspect']} judge-suspect · {n['unverified']} scorer-error"
    )
    print(f"  report : {path}")
    if write_to_mlflow:
        print("  MLflow : trace tags triage.* + run files triage/report.md, triage/cases.csv")
    print("=" * 60)
    return path


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Generate an auto-triage report for an MLflow evaluation run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/eval_report.py --latest\n"
            "  uv run python scripts/eval_report.py --run-id <run_id> --baseline <older_run_id>\n"
        ),
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-id", help="Evaluation run to analyse.")
    target.add_argument("--latest", action="store_true", help="Latest run with linked traces.")
    parser.add_argument("--baseline", help="Older run id to diff against (never guessed).")
    parser.add_argument("--per-cause", type=int, default=3, help="Traces to list per root cause.")
    parser.add_argument("--no-write", action="store_true", help="Do not tag traces / log to the run.")
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db"))

    run_id = args.run_id
    if args.latest:
        experiment_id = os.getenv("MLFLOW_EXPERIMENT_ID")
        if not experiment_id:
            print("ERROR: MLFLOW_EXPERIMENT_ID is not set (needed for --latest).")
            sys.exit(1)
        run_id = latest_evaluation_run_id(MlflowClient(), experiment_id)

    generate_report(
        run_id,
        baseline_run_id=args.baseline,
        write_to_mlflow=not args.no_write,
        per_cause=args.per_cause,
    )


if __name__ == "__main__":
    main()
