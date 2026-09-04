"""
Unit tests for domain/. These deliberately use plain `unittest`, not
Django's test client or APITestCase -- no database, no HTTP, no Django
app registry needed to run them. That's the point: if these tests need
any of that machinery to pass, the domain layer has stopped being pure,
and that's worth catching immediately.
"""

import unittest

from .job_rules import (
    PATCH_ALLOWED_FIELDS,
    compute_idempotency_key,
    is_valid_transition,
)
from .types import CompanyStatus, JobState, JobType, SplitStatus


class IdempotencyKeyTests(unittest.TestCase):
    def test_same_inputs_produce_same_key(self):
        k1 = compute_idempotency_key(1, "cwr.musicmark", "musicmark", "T-034")
        k2 = compute_idempotency_key(1, "cwr.musicmark", "musicmark", "T-034")
        self.assertEqual(k1, k2)

    def test_different_industry_id_produces_different_key(self):
        k1 = compute_idempotency_key(1, "cwr.musicmark", "musicmark", "T-034")
        k2 = compute_idempotency_key(1, "cwr.musicmark", "musicmark", "T-999")
        self.assertNotEqual(k1, k2)

    def test_blank_industry_id_is_stable(self):
        # No industry_id supplied at all vs. an explicit empty string
        # must produce the same key -- otherwise two callers describing
        # the same batch slightly differently would silently create a
        # duplicate Job.
        self.assertEqual(
            compute_idempotency_key(1, "curve.ingest", "curve"),
            compute_idempotency_key(1, "curve.ingest", "curve", ""),
        )


class StateTransitionTests(unittest.TestCase):
    def test_documented_happy_path_transitions_are_valid(self):
        self.assertTrue(is_valid_transition("queued", "running"))
        self.assertTrue(is_valid_transition("running", "succeeded"))
        self.assertTrue(is_valid_transition("running", "failed"))
        self.assertTrue(is_valid_transition("running", "child_pending"))
        self.assertTrue(is_valid_transition("child_pending", "succeeded"))

    def test_skipping_running_is_invalid(self):
        self.assertFalse(is_valid_transition("queued", "succeeded"))

    def test_terminal_states_have_no_outgoing_transitions(self):
        self.assertFalse(is_valid_transition("succeeded", "running"))
        self.assertFalse(is_valid_transition("failed", "queued"))

    def test_same_state_is_always_a_valid_no_op(self):
        # e.g. n8n re-sends the same PATCH after a retried HTTP call.
        self.assertTrue(is_valid_transition("running", "running"))

    def test_unrecognized_state_is_invalid(self):
        self.assertFalse(is_valid_transition("queued", "not-a-real-state"))


class PatchAllowListTests(unittest.TestCase):
    def test_allow_list_matches_spec_section_5_3_exactly(self):
        self.assertEqual(
            PATCH_ALLOWED_FIELDS,
            frozenset(
                {
                    "state",
                    "external_ids",
                    "object_key",
                    "checksum",
                    "n8n_run_id",
                    "error_text",
                }
            ),
        )

    def test_business_decision_fields_are_not_in_the_allow_list(self):
        # This is the actual security-relevant assertion: fields that
        # represent a legal/business decision must never be writable
        # through the n8n status-update contract.
        for forbidden in ("idempotency_key", "company", "split_status", "id"):
            self.assertNotIn(forbidden, PATCH_ALLOWED_FIELDS)


class DomainEnumSyncTests(unittest.TestCase):
    """
    Guards against domain/types.py and core/models.py's Django
    TextChoices drifting apart. See the module docstring in types.py.
    """

    def test_job_type_values_match_core_models(self):
        from core.models import Job

        domain_values = {member.value for member in JobType}
        django_values = {value for value, _label in Job.JobType.choices}
        self.assertEqual(domain_values, django_values)

    def test_job_state_values_match_core_models(self):
        from core.models import Job

        domain_values = {member.value for member in JobState}
        django_values = {value for value, _label in Job.State.choices}
        self.assertEqual(domain_values, django_values)

    def test_split_status_values_match_core_models(self):
        from core.models import WorkCase

        domain_values = {member.value for member in SplitStatus}
        django_values = {value for value, _label in WorkCase.SplitStatus.choices}
        self.assertEqual(domain_values, django_values)

    def test_company_status_values_match_core_models(self):
        from core.models import Company

        domain_values = {member.value for member in CompanyStatus}
        django_values = {value for value, _label in Company.Status.choices}
        self.assertEqual(domain_values, django_values)


if __name__ == "__main__":
    unittest.main()
