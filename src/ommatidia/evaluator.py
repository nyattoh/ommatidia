"""Objective scoring and paired condition comparison metrics.

Maintains strict separation between agent-visible payloads and gold evaluation criteria.
Implements exact denominators and small-sample uncertainty calculations.
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
    GapImportance,
    GapStatus,
    GoldStandard,
    UnderstandingState,
    Usage,
)


def score_run_objectively(
    state: UnderstandingState,
    gold: GoldStandard,
    run_id: str,
    condition: ConditionType,
    stage_breakdown: Optional[Dict[str, Usage]] = None,
) -> EvaluationMetricRecord:
    """Evaluate an execution result against the supplied gold standard.

    Guarantees:
    - Exact denominators for all rates.
    - Strict separation: this function evaluates post-run state; gold is never exposed to the agent.
    """
    if state.task_id != gold.task_id:
        raise ValueError(f"State task ID '{state.task_id}' does not match gold task ID '{gold.task_id}'")

    # 1. Final Decision Success (0 or 1)
    # Checks whether the final decision matches target_decision
    decision_matches = (state.decision == gold.target_decision)
    final_decision_success = 1 if decision_matches else 0

    # 2. Required Gap Recall (exact denominator = len(gold.required_gap_questions))
    identified_gap_texts = [g.question.lower() for g in state.gaps]
    if gold.required_gap_questions:
        matched_required_count = 0
        for req_q in gold.required_gap_questions:
            # Check for keyword or substring match in identified gaps
            req_lower = req_q.lower()
            if any(req_lower in ig or ig in req_lower for ig in identified_gap_texts):
                matched_required_count += 1
        required_gap_recall = matched_required_count / len(gold.required_gap_questions)
    else:
        required_gap_recall = 1.0

    # 3. Unnecessary Check Rate
    # Checks how many probes/checks initiated were not linked to required gaps
    total_probes = len(state.probes)
    if total_probes > 0:
        required_gap_ids = {g.id for g in state.gaps if g.importance == GapImportance.REQUIRED}
        unnecessary_probes = sum(
            1 for p in state.probes if not any(gid in required_gap_ids for gid in p.gap_ids)
        )
        unnecessary_check_rate = unnecessary_probes / total_probes
    else:
        unnecessary_check_rate = 0.0

    # 4. Valid Evidence Count (unique non-withdrawn items)
    valid_evidence = [e for e in state.evidence if e.validity == EvidenceValidity.CURRENT]
    unique_hashes = {e.content_hash for e in valid_evidence}
    valid_evidence_count = len(unique_hashes)

    # 5. Contradiction Detection Rate
    # Evaluate claims against ground_truth_verdicts
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
        required_gap_recall=required_gap_recall,
        unnecessary_check_rate=unnecessary_check_rate,
        valid_evidence_count=valid_evidence_count,
        contradiction_detection_rate=contradiction_detection_rate,
        usage=state.usage,
        stage_breakdown=stage_breakdown or {},
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
        standard error, 95% confidence interval, and small-sample caveats.
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

    # Small sample t critical value approximation for 95% two-sided
    # Using conservative t* values for df = n - 1
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

    return {
        "metric": metric_name,
        "n": n,
        "tasks": common_tasks,
        "differences": differences,
        "meanDifference": mean_diff,
        "stdDev": std_dev,
        "stdErr": std_err,
        "ci95": (ci_lower, ci_upper),
        "smallSampleNote": (
            "Caution: Small sample size (N <= 24). Results represent pilot observation "
            "and effect size estimate only, not a conclusive proof of general superiority."
        ),
    }
