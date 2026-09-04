"""
Core RCMS domain models -- first slice.

Scope (RCMS Technical Spec v1.6, Open Item 2): Company + WorkCase + Job
only. Person, Engagement, ProductCase, and RecordingLink (spec Sections
3.2, 3.3, 3.5, 3.6) are deliberately deferred to a later slice -- adding
them now would be scope creep against the spec's own "first slice"
definition. Job.product_case (spec 3.7) is likewise deferred; see the
note on that field below.

Field names and choices follow the spec exactly so the spec stays the
single source of truth for "what does RCMS know about a Company/
WorkCase/Job" -- if this file and the spec ever disagree, that's a bug
in one of them, not a design decision made only in code.
"""

from django.db import models


class Company(models.Model):
    """The customer RCMS bills. Spec Section 3.1."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PROSPECT = "prospect", "Prospect"

    name = models.CharField(max_length=255)
    legal_name = models.CharField(
        max_length=255, blank=True,
        help_text="For contracts/invoices; may differ from name.",
    )
    billing_email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROSPECT,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkCase(models.Model):
    """A composition in RCMS's care. Spec Section 3.4."""

    class SplitStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        COMPLETE = "complete", "Complete"
        REGISTERED = "registered", "Registered"

    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="work_cases",
        help_text="Owning customer.",
    )
    title = models.CharField(max_length=255)
    iswc = models.CharField(
        max_length=32, blank=True, db_index=True,
        help_text="Join key (ADR-01). Populated once registered.",
    )
    dmp_work_id = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text="Pointer into DMP (ADR-01) -- not a universal id RCMS owns.",
    )
    split_status = models.CharField(
        max_length=20, choices=SplitStatus.choices, default=SplitStatus.DRAFT,
        help_text="Gates CWR eligibility (ADR-02). Only RCMS domain logic "
                   "may change this -- see Job.PATCH allow-list in serializers.py.",
    )
    cwr_registered = models.BooleanField(
        default=False,
        help_text="Cached flag; source of truth is DMP/society ACKs.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Job(models.Model):
    """
    One batch: type, destination, state, MinIO key, n8n run id.
    Spec Section 3.7. The unit the n8n contract (spec Section 5) operates on.
    """

    class JobType(models.TextChoices):
        # Spec Section 4 -- Job Type Vocabulary
        CWR_MUSICMARK = "cwr.musicmark", "CWR - MusicMark"
        EBR_MUSICMARK = "ebr.musicmark", "EBR - MusicMark"
        CWR_MLC = "cwr.mlc", "CWR - MLC"
        MLC_BULK = "mlc.bulk", "MLC Bulk"
        MLC_CLAIM = "mlc.claim", "MLC Claim"
        ACK_IMPORT = "ack.import", "ACK Import"
        ACK_ASCAP = "ack.ascap", "ACK - ASCAP (child of cwr.musicmark)"
        ACK_BMI = "ack.bmi", "ACK - BMI (child of cwr.musicmark)"
        ACK_SOCAN = "ack.socan", "ACK - SOCAN (child of cwr.musicmark)"
        INGEST_DMP = "ingest.dmp", "Ingest - DMP"
        DISTRO_LABELGRID = "distro.labelgrid", "Distro - LabelGrid"
        CURVE_INGEST = "curve.ingest", "Curve Ingest"
        TROLLEY_PAYOUT = "trolley.payout", "Trolley Payout"
        PRO_MANUAL = "pro.manual", "PRO Manual / Exception"

    class State(models.TextChoices):
        # Spec Section 5.5 -- state machine
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CHILD_PENDING = "child_pending", "Child Pending"

    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="jobs",
    )
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    destination = models.CharField(
        max_length=64,
        help_text="e.g. musicmark, dmp, labelgrid, curve, trolley.",
    )
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.QUEUED,
    )
    object_key = models.CharField(
        max_length=512, blank=True,
        help_text="MinIO key: rcms/{customer}/{job_id}/in|out/...",
    )
    checksum = models.CharField(max_length=128, blank=True)
    n8n_run_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="Set by n8n on pickup. Enables idempotent replay (ADR-12).",
    )
    external_ids = models.JSONField(
        default=dict, blank=True,
        help_text="Society/vendor-side IDs, e.g. MusicMark batch ref.",
    )
    error_text = models.TextField(blank=True)
    idempotency_key = models.CharField(
        max_length=255, unique=True, db_index=True,
        help_text="company_id + job_type + destination + industry_id_or_batch_id "
                   "(ADR-12). Computed server-side -- see serializers.py.",
    )
    parent_job = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE,
        related_name="child_jobs",
        help_text="Child ACK events point at their parent cwr.musicmark "
                   "Job (ADR-03). A single per-society ACK closing does not "
                   "close the parent batch.",
    )
    work_case = models.ForeignKey(
        WorkCase, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="jobs",
    )
    # product_case is intentionally NOT included in this slice.
    # ProductCase (spec Section 3.5) doesn't exist yet -- it's out of scope
    # for Open Item 2. Add `product_case = models.ForeignKey(ProductCase, ...)`
    # here, plus a migration, once ProductCase ships in a later slice.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job_type} -> {self.destination} [{self.state}]"
