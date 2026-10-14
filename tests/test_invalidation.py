"""Tests for evidence deduplication, withdrawal, cascading invalidation, and falsification."""

import unittest

from ommatidia.invalidation import deduplicate_evidence, invalidate_evidence
from ommatidia.state import create_initial_state
from ommatidia.types import (
    Assessment,
    AssessmentVerdict,
    Claim,
    ClaimRole,
    ClaimStatus,
    Evidence,
    EvidenceKind,
    EvidenceValidity,
    Gap,
    GapImportance,
    GapKind,
    GapStatus,
    Resolution,
    ResolutionReason,
)
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


class TestInvalidationAndDeduplication(unittest.TestCase):
    def setUp(self) -> None:
        fixtures = get_mechanism_check_fixtures()
        self.task, _ = fixtures[0]
        self.state = create_initial_state(self.task)

    def test_duplicate_evidence_rejection(self) -> None:
        ev1 = Evidence(
            id="ev_original",
            kind=EvidenceKind.DOCUMENT,
            locator="doc1.txt",
            source_group="group_a",
            retrieved_at="2026-10-14T01:00:00Z",
            version="1.0",
            scope="scope1",
            passage="Sample passage text",
            content_hash="1111111111111111111111111111111111111111111111111111111111111111",
        )
        # Duplicate with different ID but identical content hash
        ev2_dup = Evidence(
            id="ev_duplicate",
            kind=EvidenceKind.DOCUMENT,
            locator="doc2.txt",
            source_group="group_b",
            retrieved_at="2026-10-14T01:05:00Z",
            version="1.0",
            scope="scope1",
            passage="Sample passage text",
            content_hash="1111111111111111111111111111111111111111111111111111111111111111",
        )

        accepted, rejected = deduplicate_evidence([ev1], [ev2_dup])
        self.assertEqual(len(accepted), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].id, "ev_duplicate")

    def test_evidence_withdrawal_cascades_to_claims_and_gaps(self) -> None:
        ev = Evidence(
            id="ev_critical",
            kind=EvidenceKind.CODE,
            locator="src/cache.py",
            source_group="codebase",
            retrieved_at="2026-10-14T01:00:00Z",
            version="git-abc",
            scope="cache",
            passage="cache.evict() is async",
            content_hash="2222222222222222222222222222222222222222222222222222222222222222",
        )
        self.state.evidence.append(ev)

        # Claim supported by this evidence
        asm = Assessment(
            claim_id="claim_01",
            evidence_ids=[ev.id],
            verdict=AssessmentVerdict.SUPPORTS,
            scope_matched=True,
            reason="Confirmed in code",
        )
        claim = Claim(
            id="claim_01",
            role=ClaimRole.ANSWER_CLAIM,
            text="Cache eviction is async",
            scope="cache",
            status=ClaimStatus.SUPPORTED,
            assessments=[asm],
        )
        self.state.claims.append(claim)

        # Gap resolved using this evidence
        res = Resolution(
            reason=ResolutionReason.SUPPORTED,
            evidence_ids=[ev.id],
            explanation="Code verified async",
        )
        gap = Gap(
            id="gap_01",
            kind=GapKind.MISSING_FACT,
            lens_id="lens_test",
            question="Is eviction async?",
            trigger_refs=["code"],
            why_it_matters="Concurrency",
            importance=GapImportance.REQUIRED,
            claim_ids=[claim.id],
            status=GapStatus.RESOLVED,
            resolution=res,
        )
        self.state.gaps.append(gap)

        # Now withdraw ev_critical (e.g. outdated branch or revoked benchmark data)
        report = invalidate_evidence(
            self.state,
            target_evidence_ids=[ev.id],
            reason="Branch was stale and subsequently reverted upstream",
            action=EvidenceValidity.WITHDRAWN,
        )

        # Verify cascades
        self.assertIn(ev.id, report["invalidatedEvidenceIds"])
        self.assertIn(claim.id, report["claimsModified"])
        self.assertIn(gap.id, report["gapsReopened"])

        # Check state: claim status should revert to UNVERIFIED
        self.assertEqual(claim.status, ClaimStatus.UNVERIFIED)
        self.assertEqual(len(claim.assessments), 0)

        # Check state: gap status should revert to OPEN and resolution cleared
        self.assertEqual(gap.status, GapStatus.OPEN)
        self.assertIsNone(gap.resolution)

        # Target evidence validity must be WITHDRAWN
        ev_in_state = next(e for e in self.state.evidence if e.id == ev.id)
        self.assertEqual(ev_in_state.validity, EvidenceValidity.WITHDRAWN)


if __name__ == "__main__":
    unittest.main()
