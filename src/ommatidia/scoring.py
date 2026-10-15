"""Score saved traces; unavailable observations are errors, not invented metrics."""

import math
import random
from statistics import NormalDist

from ommatidia.evaluator import compute_wilcoxon_signed_rank, wilson_score_interval_cc
from ommatidia.types import EvidenceValidity, GoldStandard, UnderstandingState


class MetricUnavailable(ValueError):
    pass


def score_saved_trial(record, rubric, metrics=("fda", "recallCrit", "dsc", "warrantedAbstention", "unwarrantedAbstention")):
    if isinstance(rubric, GoldStandard):
        rubric = rubric.to_dict()
    if rubric.get("taskId") != record.task_id:
        raise ValueError("Rubric taskId mismatch")
    verdicts = rubric.get("groundTruthVerdicts", {})
    target = rubric.get("targetVerdict") or verdicts.get(f"claim_{record.task_id}_01")
    if target is None and len(set(verdicts.values())) == 1:
        target = next(iter(verdicts.values()))
    if target not in ("supported", "contradicted", "disputed", "inconclusive"):
        raise MetricUnavailable("Unambiguous target verdict is required")
    if not record.final_state or not record.final_judgement:
        raise MetricUnavailable("Saved final state and judgement are required")
    state = UnderstandingState.from_dict(record.final_state)
    fj = record.final_judgement
    failed = record.status in ("failed", "invalid_response")
    input_hashes = {e.content_hash for e in state.task.evidence}
    verified = {e.content_hash: e for e in state.evidence
                if e.validity == EvidenceValidity.CURRENT and e.content_hash not in input_hashes}
    retrieved = {e.content_hash for e in fj.cited_evidence
                 if e.content_hash in verified and e.locator == verified[e.content_hash].locator
                 and e.source_group == verified[e.content_hash].source_group}
    if failed:
        retrieved = set()
    critical = set(rubric.get("criticalEvidenceHashes", []))
    result = {}
    for metric in metrics:
        if metric == "fda":
            result[metric] = int(not failed and fj.verdict == target)
        elif metric == "recallCrit":
            if not critical:
                raise MetricUnavailable("Recall_crit requires a non-empty mandatory evidence set")
            result[metric] = len(critical & retrieved) / len(critical)
        elif metric == "dsc":
            result[metric] = len({e.source_group for e in verified.values() if e.source_group})
        elif metric in ("warrantedAbstention", "unwarrantedAbstention"):
            applicable = (target == "inconclusive") == (metric == "warrantedAbstention")
            result[metric] = int(not failed and fj.verdict == "inconclusive") if applicable else None
        elif metric == "far":
            if failed:
                raise MetricUnavailable("FAR requires a complete successful candidate trace")
            labels = rubric.get("probeLabels", {})
            ids = {probe.id for probe in state.probes}
            if ids - labels.keys() or any(labels[pid] not in ("genuine", "spurious") for pid in ids):
                raise MetricUnavailable("FAR requires independent labels for every generated probe")
            result[metric] = sum(labels[pid] == "spurious" for pid in ids) / len(ids) if ids else 0.0
        elif metric == "requiredGapRecall":
            required = set(rubric.get("requiredGapQuestions", []))
            if not required:
                raise MetricUnavailable("Gap recall requires required questions")
            resolved = {g.question for g in state.gaps if g.status.value == "resolved" and g.resolution}
            result[metric] = len(required & resolved) / len(required)
        elif metric in ("efficiencyTool", "efficiencyTime"):
            known = record.usage_known if metric == "efficiencyTool" else True
            denominator = record.usage.tool_calls if metric == "efficiencyTool" else (
                record.wall_elapsed_ms / 1000 if record.wall_elapsed_ms is not None else None)
            if not known or denominator is None or denominator <= 0 or not critical:
                raise MetricUnavailable(f"{metric} denominator is unavailable or zero")
            result[metric] = len(critical & retrieved) / denominator
        elif metric == "decisionDegradation":
            if "initialVerdict" not in rubric:
                raise MetricUnavailable("DDR requires the frozen initial verdict")
            result[metric] = int(failed or fj.verdict != target) if rubric["initialVerdict"] == target else None
        elif metric == "candidatePrecision":
            labels = rubric.get("gapLabels", {})
            ids = {g.id for g in state.gaps}
            if not ids or ids - labels.keys() or any(labels[gid] not in ("genuine", "spurious") for gid in ids):
                raise MetricUnavailable("Candidate precision requires independently labelled candidate gaps")
            result[metric] = sum(labels[gid] == "genuine" for gid in ids) / len(ids)
        else:
            raise MetricUnavailable(f"Metric is not specified or supported: {metric}")
    return result


def validate_matrix(records, conditions, task_ids, run_id=None):
    expected = set(task_ids)
    if len(expected) != 24:
        raise ValueError("The preregistered denominator is exactly 24 distinct cases")
    matrix = {condition: {} for condition in conditions}
    identities = set()
    for record in records:
        if record.condition.value not in matrix:
            continue
        if record.replication != 1 or (run_id is not None and record.run_id != run_id):
            raise ValueError("Mixed run or replication in saved matrix")
        if record.task_id in matrix[record.condition.value]:
            raise ValueError("Duplicate trial in saved matrix")
        matrix[record.condition.value][record.task_id] = record
        identities.add((record.code_hash, record.prompt_hash, record.spec_hash, record.executor))
    if len(identities) != 1 or any(part is None for identity in identities for part in identity):
        raise ValueError("Mixed or missing runtime provenance")
    for condition, trials in matrix.items():
        if set(trials) != expected:
            raise ValueError(f"Condition {condition} requires all 24 cases; missing or extra trial")
    return matrix


def bca_interval(values, resamples=10000, seed=1701):
    n = len(values)
    mean = sum(values) / n
    if n < 2 or len(set(values)) == 1:
        return {"ci95": None, "reason": "Degenerate paired distribution", "resamples": resamples}
    rng = random.Random(seed)
    boot = sorted(sum(rng.choices(values, k=n)) / n for _ in range(resamples))
    normal = NormalDist()
    proportion = (sum(x < mean for x in boot) + 0.5 * sum(x == mean for x in boot)) / resamples
    z0 = normal.inv_cdf(min(1 - 0.5 / resamples, max(0.5 / resamples, proportion)))
    jack = [(sum(values) - x) / (n - 1) for x in values]
    jack_mean = sum(jack) / n
    delta = [jack_mean - x for x in jack]
    denom = 6 * sum(x*x for x in delta)**1.5
    acceleration = sum(x**3 for x in delta) / denom if denom else 0
    bounds = []
    for alpha in (0.025, 0.975):
        z = normal.inv_cdf(alpha)
        divisor = 1 - acceleration * (z0 + z)
        if abs(divisor) < 1e-12:
            return {"ci95": None, "reason": "Undefined BCa quantile", "resamples": resamples}
        quantile = normal.cdf(z0 + (z0 + z) / divisor)
        bounds.append(boot[min(resamples-1, max(0, int(quantile * (resamples-1))))])
    return {"ci95": bounds, "resamples": resamples, "seed": seed, "method": "BCa paired case bootstrap"}


def analyse_saved_trials(records, task_ids, counterexample_ids):
    from ommatidia.harness import compute_exact_mcnemar, compute_holm_bonferroni
    matrix = validate_matrix(records, ["B", "C", "D", "E"], task_ids)
    subset = set(counterexample_ids)
    if len(subset) != 12 or not subset.issubset(set(task_ids)):
        raise ValueError("H4 requires exactly 12 frozen counterexample IDs within the 24 cases")

    def value(condition, tid, metric):
        record = matrix[condition][tid]
        number = record.metrics.get(metric)
        if number is None or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise MetricUnavailable(f"Saved {metric} unavailable: {condition}/{tid}")
        if metric == "fda" and number not in (0, 1):
            raise ValueError("FDA must be binary")
        return number

    reports = []
    for hypothesis, baseline, metric, ids in [("H1", "C", "fda", sorted(task_ids)),
                                              ("H2", "D", "dsc", sorted(task_ids)),
                                              ("H3", "D", "far", sorted(task_ids)),
                                              ("H4", "B", "fda", sorted(subset))]:
        primary = [value("E", tid, metric) for tid in ids]
        control = [value(baseline, tid, metric) for tid in ids]
        differences = [p - b for p, b in zip(primary, control)]
        if metric == "fda":
            b = sum(p == 1 and c == 0 for p, c in zip(primary, control))
            c = sum(p == 0 and c == 1 for p, c in zip(primary, control))
            test = {"method": "exact McNemar", "b": b, "c": c, "pValue": compute_exact_mcnemar(b, c)}
            test["primaryWilson95"] = wilson_score_interval_cc(sum(primary), len(ids))
            test["baselineWilson95"] = wilson_score_interval_cc(sum(control), len(ids))
        else:
            test = {"method": "paired Wilcoxon", **compute_wilcoxon_signed_rank(differences)}
            test["bca"] = bca_interval(differences)
        if hypothesis == "H1":
            recall_diff = [value("E", tid, "recallCrit") - value("C", tid, "recallCrit") for tid in ids]
            test["recallWilcoxon"] = compute_wilcoxon_signed_rank(recall_diff)
        reports.append({"hypothesis": hypothesis, "baseline": baseline, "metric": metric,
                        "sampleSize": len(ids), "meanDifference": sum(differences)/len(ids), "test": test})
    raw = [report["test"]["pValue"] for report in reports]
    # An uncomputable hypothesis stays in the four-member family and is never declared significant.
    adjusted = compute_holm_bonferroni([p if p is not None else 1.0 for p in raw])
    for report, p, adj in zip(reports, raw, adjusted):
        report["holmAdjustedP"] = adj if p is not None else None
        report["significant"] = p is not None and adj < 0.05
    return {"sampleSize": 24, "familySize": 4, "multiplicity": "Holm-Bonferroni", "hypotheses": reports}
