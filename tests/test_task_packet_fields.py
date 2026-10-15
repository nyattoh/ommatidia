"""TaskPacket domain/availableSources contract; in-memory synthetic data only."""

from dataclasses import replace

import pytest

from ommatidia.runtime import condition_graph, render_prompt, step_payload
from ommatidia.types import ConditionType, TaskPacket
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures

SOURCES = [
    {
        "sourceGroup": "g1",
        "description": "synthetic source",
        "entryLocator": "src/a.txt",
    },
    {"sourceGroup": "g2", "description": "second source", "entryLocator": "docs/b.txt"},
]


def packet_dict(**extra):
    data = get_mechanism_check_fixtures()[0][0].to_dict()
    data.pop("domain", None)
    data.pop("availableSources", None)
    return {**data, **extra}


def test_roundtrip_preserves_fields():
    data = packet_dict(domain="document_research", availableSources=SOURCES)
    out = TaskPacket.from_dict(data).to_dict()
    assert out["domain"] == "document_research"
    assert out["availableSources"] == SOURCES
    assert out == data


def test_legacy_packet_loads_without_inventing_fields():
    task = TaskPacket.from_dict(packet_dict())
    assert task.domain is None and task.available_sources is None
    out = task.to_dict()
    assert "domain" not in out and "availableSources" not in out
    payload = step_payload(
        task, ConditionType.A, condition_graph(ConditionType.A)[0], 1, "r"
    )
    assert "domain" not in payload and "availableSources" not in payload


def test_empty_sources_is_present_not_absent():
    out = TaskPacket.from_dict(
        packet_dict(domain="software_engineering", availableSources=[])
    ).to_dict()
    assert out["availableSources"] == []


@pytest.mark.parametrize(
    "bad",
    [
        {"domain": None, "availableSources": None},
        {"domain": None, "availableSources": []},
        {"domain": "document_research", "availableSources": None},
        {"domain": "document_research"},
        {"availableSources": SOURCES},
        {"availableSources": []},
        {"domain": None},
        {"availableSources": None},
        {"domain": "other", "availableSources": []},
        {"domain": 3, "availableSources": []},
        {"domain": "", "availableSources": []},
        {"domain": "document_research", "availableSources": "x"},
        {"domain": "document_research", "availableSources": {"sourceGroup": "g"}},
        {"domain": "document_research", "availableSources": ["x"]},
        {
            "domain": "document_research",
            "availableSources": [{"sourceGroup": "g", "description": "d"}],
        },
        {
            "domain": "document_research",
            "availableSources": [
                {"sourceGroup": "g", "description": "d", "entryLocator": None}
            ],
        },
        {
            "domain": "document_research",
            "availableSources": [
                {"sourceGroup": 1, "description": "d", "entryLocator": "l"}
            ],
        },
    ],
)
def test_invalid_shapes_rejected(bad):
    with pytest.raises(ValueError):
        TaskPacket.from_dict(packet_dict(**bad))


def test_empty_strings_in_source_items_are_schema_valid():
    row = {"sourceGroup": "", "description": "", "entryLocator": ""}
    data = packet_dict(domain="document_research", availableSources=[row])
    assert TaskPacket.from_dict(data).to_dict() == data


def test_direct_construction_requires_both_fields():
    base = TaskPacket.from_dict(packet_dict())
    with pytest.raises(ValueError):
        replace(base, domain="document_research")
    with pytest.raises(ValueError):
        replace(base, available_sources=[])


@pytest.mark.parametrize("condition", list(ConditionType))
def test_every_condition_payload_carries_fields(condition):
    task = TaskPacket.from_dict(
        packet_dict(domain="workflow_automation", availableSources=SOURCES)
    )
    steps = condition_graph(condition)
    assert steps
    for i, step in enumerate(steps, 1):
        payload = step_payload(task, condition, step, i, "run")
        assert payload["domain"] == "workflow_automation"
        assert payload["availableSources"] == SOURCES
        render_prompt(payload)  # public guard still runs


def test_public_guard_still_rejects_private_locator_in_sources():
    task = TaskPacket.from_dict(
        packet_dict(
            domain="document_research",
            availableSources=[
                {
                    "sourceGroup": "g",
                    "description": "d",
                    "entryLocator": "x/gold/a.json",
                }
            ],
        )
    )
    with pytest.raises(ValueError):
        step_payload(
            task, ConditionType.A, condition_graph(ConditionType.A)[0], 1, "run"
        )
