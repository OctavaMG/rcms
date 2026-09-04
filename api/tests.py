"""
HTTP-level contract tests for /api/jobs/. These exercise the actual
request/response cycle (auth, status codes, JSON shape) -- the
underlying rules these endpoints rely on (idempotency, the PATCH
allow-list, state transitions) are unit-tested in isolation in
domain/tests.py. This file proves the API layer wires those rules up
correctly; it doesn't re-prove the rules themselves.
"""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from core.models import Company, Job


class JobContractTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="n8n", password="testpass123")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.company = Company.objects.create(name="Exceed Music", status=Company.Status.ACTIVE)

    def test_create_job_is_idempotent(self):
        """Same company/job_type/destination/industry_id -> same Job, not a duplicate."""
        url = reverse("job-list-create")
        payload = {
            "company": self.company.id,
            "job_type": Job.JobType.CWR_MUSICMARK,
            "destination": "musicmark",
            "industry_id": "T-034.524.680-1",
        }

        first = self.client.post(url, payload, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(Job.objects.count(), 1)

        second = self.client.post(url, payload, format="json")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_different_industry_id_creates_a_new_job(self):
        url = reverse("job-list-create")
        base_payload = {
            "company": self.company.id,
            "job_type": Job.JobType.CWR_MUSICMARK,
            "destination": "musicmark",
        }
        self.client.post(url, {**base_payload, "industry_id": "WORK-A"}, format="json")
        self.client.post(url, {**base_payload, "industry_id": "WORK-B"}, format="json")
        self.assertEqual(Job.objects.count(), 2)

    def test_patch_allow_list_is_enforced(self):
        job = Job.objects.create(
            company=self.company,
            job_type=Job.JobType.CWR_MUSICMARK,
            destination="musicmark",
            idempotency_key="test-key-001",
            state=Job.State.RUNNING,
        )
        other_company = Company.objects.create(name="Other Co")

        url = reverse("job-detail", args=[job.id])
        response = self.client.patch(
            url,
            {
                "state": Job.State.SUCCEEDED,
                "n8n_run_id": "run-abc-123",
                "idempotency_key": "HACKED-KEY",
                "company": other_company.id,
                "checksum": "sha256:deadbeef",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()

        self.assertEqual(job.state, Job.State.SUCCEEDED)
        self.assertEqual(job.n8n_run_id, "run-abc-123")
        self.assertEqual(job.checksum, "sha256:deadbeef")
        self.assertEqual(job.idempotency_key, "test-key-001")
        self.assertEqual(job.company_id, self.company.id)

    def test_patch_rejects_invalid_state_transition(self):
        """
        New in this slice: a PATCH that skips a state (queued straight
        to succeeded) is rejected with 400, not silently accepted.
        """
        job = Job.objects.create(
            company=self.company,
            job_type=Job.JobType.CWR_MUSICMARK,
            destination="musicmark",
            idempotency_key="test-key-002",
            state=Job.State.QUEUED,
        )
        url = reverse("job-detail", args=[job.id])
        response = self.client.patch(url, {"state": Job.State.SUCCEEDED}, format="json")

        self.assertEqual(response.status_code, 400)
        job.refresh_from_db()
        self.assertEqual(job.state, Job.State.QUEUED)  # unchanged

    def test_patch_allows_valid_transition(self):
        job = Job.objects.create(
            company=self.company,
            job_type=Job.JobType.CWR_MUSICMARK,
            destination="musicmark",
            idempotency_key="test-key-003",
            state=Job.State.QUEUED,
        )
        url = reverse("job-detail", args=[job.id])
        response = self.client.patch(url, {"state": Job.State.RUNNING}, format="json")

        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.state, Job.State.RUNNING)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.credentials()
        url = reverse("job-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
