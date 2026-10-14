"""Objective scoring and paired condition comparison metrics.

Maintains strict separation between agent-visible payloads and gold evaluation criteria.
Implements exact denominators, Wilson score CIs, Wilcoxon signed-rank tests,
and small-sample uncertainty calculations per research/EVALUATION_SPEC.md.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from ommatidia.types import (
    ClaimStatus,
    ConditionType,
    Decision,
    EvaluationMetricRecord,
    EvidenceValidity,
    FinalJudgement,
    GapImportance,
    GapStatus,
    GoldStandard,
    UnderstandingState,
    Usage,
)


def wilson_score_interval_cc(
    successes: int, total: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """Compute Wilson score confidence interval with continuity correction (Newcombe 1998)."""
    if total <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054  # 95% two-sided
    p = successes / total
    q = 1.0 - p
    denom = 2 * (total + z * z)

    # Lower bound
    if successes == 0:
        lower = 0.0
    else:
        radicand_lower = z * z - 2.0 - (1.0 / total) + 4.0 * p * (total * q + 1.0)
        sqrt_term_lower = z * math.sqrt(max(0.0, radicand_lower))
        lower = max(0.0, (2.0 * total * p + z * z - 1.0 - sqrt_term_lower) / denom)

    # Upper bound
    if successes == total:
        upper = 1.0
    else:
        radicand_upper = z * z + 2.0 - (1.0 / total) + 4.0 * p * (total * q - 1.0)
        sqrt_term_upper = z * math.sqrt(max(0.0, radicand_upper))
        upper = min(1.0, (2.0 * total * p + z * z + 1.0 + sqrt_term_upper) / denom)

    return (lower, upper)


def compute_wilcoxon_signed_rank(differences: List[float]) -> Dict[str, Any]:
    """Paired Wilcoxon signed-rank test following EVALUATION_SPEC.md Section 5.2.

    Rules:
    - Pairs whose difference is exactly zero are excluded.
    - Tied absolute differences receive average ranks.
    - Normal approximation without continuity correction is used.
    - If fewer than 6 non-zero pairs remain, report as not computable and inconclusive.
    """
    non_zero = [float(d) for d in differences if d != 0.0]
    n_r = len(non_zero)
    if n_r < 6:
        return {
            "computable": False,
            "verdict": "inconclusive",
            "reason": f"Fewer than 6 non-zero pairs remain (nR = {n_r} < 6).",
            "nR": n_r,
            "wStatistic": None,
            "zScore": None,
            "pValue": None,
        }

    # Sort by absolute difference
    abs_diffs = [(abs(d), d) for d in non_zero]
    abs_diffs.sort(key=lambda x: x[0])

    # Assign ranks with average rank for ties
    ranks: List[Tuple[float, float]] = []  # (rank, original_diff)
    i = 0
    tie_counts: List[int] = []
    while i < n_r:
        j = i
        while j < n_r and abs_diffs[j][0] == abs_diffs[i][0]:
            j += 1
        tie_size = j - i
        if tie_size > 1:
            tie_counts.append(tie_size)
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks.append((avg_rank, abs_diffs[k][1]))
        i = j

    # Sum of ranks for positive differences
    w_plus = sum(r for r, d in ranks if d > 0)
    w_minus = sum(r for r, d in ranks if d < 0)
    w_stat = min(w_plus, w_minus)

    # Expected value and variance under null hypothesis
    mean_w = n_r * (n_r + 1) / 4.0
    tie_adjustment = sum(t * (t * t - 1) for t in tie_counts) / 48.0
    var_w = (n_r * (n_r + 1) * (2 * n_r + 1) / 24.0) - tie_adjustment
    std_w = math.sqrt(max(1e-9, var_w))

    # Normal approximation without continuity correction per specification
    z_score = (w_plus - mean_w) / std_w
    # Two-sided p-value
    p_value = math.erfc(abs(z_score) / math.sqrt(2.0))

    return {
        "computable": True,
        "verdict": "significant" if p_value < 0.05 else "not_significant",
        "nR": n_r,
        "wPlus": w_plus,
        "wMinus": w_minus,
        "wStatistic": w_stat,
        "zScore": z_score,
        "pValue": p_value,
        "tieAdjustment": tie_adjustment,
    }


def score_run_objectively(
    state: UnderstandingState,
    gold: GoldStandard,
    run_id: str,
    condition: ConditionType,
    stage_breakdown: Optional[Dict[str, Usage]] = None,
    final_judgement: Optional[FinalJudgement] = None,
) -> EvaluationMetricRecord:
    """Evaluate an execution result against the supplied gold standard.

    Guarantees:
    - Exact denominators for all rates.
    - Strict separation: this function evaluates post-run state; gold is never exposed to the agent.
    - Aligned with research/EVALUATION_SPEC.md (FDA, Recall_crit, FAR, DSC, WAR, UAR).
    """
    if state.task_id != gold.task_id:
        raise ValueError(f"State task ID '{state.task_id}' does not match gold task ID '{gold.task_id}'")

    # Resolve FinalJudgement
    fj = final_judgement or state.final_judgement or state.synthesize_final_judgement()

    # Ground truth verdict Vi*
    target_verdict = None
    if gold.ground_truth_verdicts:
        target_verdict = gold.ground_truth_verdicts.get(f"claim_{gold.task_id}_01")
        if target_verdict is None:
            target_verdict = next(iter(gold.ground_truth_verdicts.values()))
    if target_verdict is None:
        target_verdict = "supported" if gold.target_decision == Decision.READY_FOR_REQUESTED_STEP else "inconclusive"

    # 1. Final Decision Accuracy (FDA)
    agent_verdict = fj.verdict
    fda = 1 if agent_verdict == target_verdict else 0
    final_decision_success = fda

    # 2. Critical Item Recall (Recall_crit)
    cited_hashes = {e.content_hash for e in fj.cited_evidence}
    for e in state.evidence:
        if e.validity == EvidenceValidity.CURRENT:
            cited_hashes.add(e.content_hash)

    critical_hashes = set(gold.critical_evidence_hashes)
    if critical_hashes:
        retrieved_crit = critical_hashes.intersection(cited_hashes)
        recall_crit = len(retrieved_crit) / len(critical_hashes)
    else:
        recall_crit = 1.0

    # 3. False Alarm Rate (FAR) / Unnecessary Check Rate
    total_probes = len(state.probes)
    if total_probes > 0:
        required_gap_ids = {g.id for g in state.gaps if g.importance == GapImportance.REQUIRED}
        spurious_probes = sum(
            1 for p in state.probes if not any(gid in required_gap_ids for gid in p.gap_ids)
        )
        far = spurious_probes / total_probes
    else:
        far = 0.0
    unnecessary_check_rate = far

    # 4. Disjoint Source Coverage (DSC)
    unique_sources = set()
    for e in state.evidence:
        if e.validity == EvidenceValidity.CURRENT and e.source_group:
            unique_sources.add(e.source_group)
    for p in state.probes:
        unique_sources.update(p.source_groups)
    dsc = len(unique_sources)

    # 5. Abstention classification (WAR / UAR)
    is_unresolvable = (target_verdict == "inconclusive")
    if is_unresolvable:
        warranted_abstention = 1 if agent_verdict == "inconclusive" else 0
        unwarranted_abstention = None
    else:
        warranted_abstention = None
        unwarranted_abstention = 1 if agent_verdict == "inconclusive" else 0

    # 6. Physical execution efficiency ratios
    critical_count = len(critical_hashes.intersection(cited_hashes)) if critical_hashes else 0
    efficiency_tool = critical_count / max(1, state.usage.tool_calls)
    efficiency_time = critical_count / max(0.001, state.usage.elapsed_ms / 1000.0)

    # 7. Valid evidence count
    valid_evidence = [e for e in state.evidence if e.validity == EvidenceValidity.CURRENT]
    unique_ev_hashes = {e.content_hash for e in valid_evidence}
    valid_evidence_count = len(unique_ev_hashes)

    # 8. Contradiction detection rate
    contradiction_targets = {
        cid: expected for cid, expected in gold.ground_truth_verdicts.items()
        if expected in ("contradicted", "refuted")
    }
    if contradiction_targets:
        detected_contradictions = 0
        claim_map = {c.id: c for c in state.claims}
        for cid in contradiction_targets:
            claim = claim_map.get(cid)
            if claim and claim.status in (ClaimStatus.CONTRADICTED, ClaimStatus.DISPUTED):
                detected_contradictions += 1
        contradiction_detection_rate = detected_contradictions / len(contradiction_targets)
    else:
        contradiction_detection_rate = 1.0

    return EvaluationMetricRecord(
        task_id=state.task_id,
        condition=condition,
        run_id=run_id,
        final_decision_success=final_decision_success,
        required_gap_recall=recall_crit,
        unnecessary_check_rate=unnecessary_check_rate,
        valid_evidence_count=valid_evidence_count,
        contradiction_detection_rate=contradiction_detection_rate,
        usage=state.usage,
        stage_breakdown=stage_breakdown or {},
        fda=fda,
        recall_crit=recall_crit,
        far=far,
        dsc=dsc,
        warranted_abstention=warranted_abstention,
        unwarranted_abstention=unwarranted_abstention,
        efficiency_tool=efficiency_tool,
        efficiency_time=efficiency_time,
        final_judgement=fj,
    )


def compute_paired_differences(
    records_primary: List[EvaluationMetricRecord],
    records_baseline: List[EvaluationMetricRecord],
    metric_name: str = "final_decision_success",
) -> Dict[str, Any]:
    """Compute paired per-case metric differences and small-sample statistics.

    Args:
        records_primary: Metric records from Condition E (or candidate condition).
        records_baseline: Metric records from baseline condition (e.g., D, B, C, A).
        metric_name: Attribute name on EvaluationMetricRecord to compare.

    Returns:
        Dictionary with sample size, exact paired differences, mean difference,
        standard error, 95% confidence interval, Wilcoxon test, and small-sample caveats.
    """
    primary_map = {r.task_id: getattr(r, metric_name) for r in records_primary}
    baseline_map = {r.task_id: getattr(r, metric_name) for r in records_baseline}

    common_tasks = sorted(list(set(primary_map.keys()).intersection(set(baseline_map.keys()))))
    n = len(common_tasks)
    if n == 0:
        return {"n": 0, "error": "No overlapping tasks found for paired comparison"}

    differences: List[float] = [
        float(primary_map[tid]) - float(baseline_map[tid]) for tid in common_tasks
    ]

    mean_diff = sum(differences) / n
    variance = sum((d - mean_diff) ** 2 for d in differences) / (n - 1) if n > 1 else 0.0
    std_dev = math.sqrt(variance)
    std_err = std_dev / math.sqrt(n) if n > 0 else 0.0

    # Defect 1 remediation: When sample variance is 0.0, do not emit [0.0, 0.0]
    if variance == 0.0 or n < 2:
        ci95 = None
        ci_note = (
            "Confidence interval undefined: sample variance is zero across matched pairs. "
            "In small samples (N <= 24), zero observed variance indicates insufficient sample power "
            "rather than zero population uncertainty."
        )
    else:
        t_star_table = {
            1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57,
            6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23,
            15: 2.13, 20: 2.09, 23: 2.07, 24: 2.06, 30: 2.04,
        }
        df = n - 1
        t_crit = 1.96
        for k in sorted(t_star_table.keys()):
            if df <= k:
                t_crit = t_star_table[k]
                break

        ci_lower = mean_diff - (t_crit * std_err)
        ci_upper = mean_diff + (t_crit * std_err)
        ci95 = (ci_lower, ci_upper)
        ci_note = None

    wilcoxon = compute_wilcoxon_signed_rank(differences)

    return {
        "metric": metric_name,
        "n": n,
        "tasks": common_tasks,
        "differences": differences,
        "meanDifference": mean_diff,
        "stdDev": std_dev,
        "stdErr": std_err,
        "ci95": ci95,
        "ciNote": ci_note,
        "wilcoxon": wilcoxon,
        "smallSampleNote": (
            "Caution: Small sample size (N <= 24). Results represent pilot observation "
            "and effect size estimate only, not a conclusive proof of general superiority."
        ),
    }
