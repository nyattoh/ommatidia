"""Task provenance regressions using only synthetic trial records."""

from dataclasses import replace
from hashlib import sha256

import pytest

from ommatidia.harness import TrialRecord
from ommatidia.scoring import validate_matrix
from ommatidia.types import ConditionType


CONDITIONS = ("B", "C", "D", "E")
RUN_ID = "synthetic_task_provenance"
TASK_IDS = tuple(f"synthetic_task_provenance_{index:02d}" for index in range(24))


def synthetic_matrix():
    return [
        TrialRecord(
            task_id=task_id,
            condition=ConditionType(condition),
            run_id=RUN_ID,
            replication=1,
            code_hash="synthetic_code_hash",
            prompt_hash="synthetic_prompt_hash",
            spec_hash="synthetic_spec_hash",
            executor="synthetic_executor",
            task_hash=sha256(f"Synthetic task packet: {task_id}".encode()).hexdigest(),
        )
        for task_id in TASK_IDS
        for condition in CONDITIONS
    ]


def test_valid_matrix_accepts_distinct_hashes_per_task():
    records = synthetic_matrix()

    matrix = validate_matrix(records, CONDITIONS, TASK_IDS, run_id=RUN_ID)

    assert set(matrix) == set(CONDITIONS)
    assert all(set(trials) == set(TASK_IDS) for trials in matrix.values())
    assert len({record.task_hash for record in records}) == 24
    for task_id in TASK_IDS:
        paired = [matrix[condition][task_id] for condition in CONDITIONS]
        assert len({record.task_hash for record in paired}) == 1
        assert all(record.task_hash is not None for record in paired)
    for record in records:
        assert matrix[record.condition.value][record.task_id] is record


def test_matrix_rejects_task_hash_mismatch_between_paired_conditions():
    records = synthetic_matrix()
    records[1] = replace(
        records[1], task_hash=sha256(b"Different synthetic task packet").hexdigest()
    )
    assert records[0].task_id == records[1].task_id
    assert records[0].condition != records[1].condition
    assert records[0].task_hash != records[1].task_hash

    with pytest.raises(ValueError):
        validate_matrix(records, CONDITIONS, TASK_IDS, run_id=RUN_ID)


def test_matrix_rejects_null_task_hash():
    records = synthetic_matrix()
    records[1] = replace(records[1], task_hash=None)

    with pytest.raises(ValueError):
        validate_matrix(records, CONDITIONS, TASK_IDS, run_id=RUN_ID)


def test_matrix_ignores_provenance_in_unselected_condition():
    records = synthetic_matrix()
    unselected = replace(
        records[0],
        condition=ConditionType.A,
        run_id="synthetic_unselected_run",
        replication=2,
        task_hash=None,
        code_hash=None,
        prompt_hash=None,
        spec_hash=None,
        executor="synthetic_unselected_executor",
    )
    expected = validate_matrix(records, CONDITIONS, TASK_IDS, run_id=RUN_ID)

    assert (
        validate_matrix([unselected, *records], CONDITIONS, TASK_IDS, run_id=RUN_ID)
        == expected
    )
