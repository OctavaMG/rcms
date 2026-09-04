"""
Pure domain vocabulary. No Django imports here, by design -- this module
must be importable and unit-testable with nothing but the Python
standard library.

These are the canonical string values. `core/models.py` defines its own
Django `TextChoices` classes (Django Admin and migrations need that
specific type), but their values are asserted to match these in
`domain/tests.py` -- so the two can't silently drift apart. If you add,
rename, or remove a value, update both, and the test will fail loudly
if you forget one side.
"""

from enum import StrEnum


class JobType(StrEnum):
    """RCMS Technical Spec v1.6, Section 4 -- Job Type Vocabulary."""

    CWR_MUSICMARK = "cwr.musicmark"
    EBR_MUSICMARK = "ebr.musicmark"
    CWR_MLC = "cwr.mlc"
    MLC_BULK = "mlc.bulk"
    MLC_CLAIM = "mlc.claim"
    ACK_IMPORT = "ack.import"
    ACK_ASCAP = "ack.ascap"
    ACK_BMI = "ack.bmi"
    ACK_SOCAN = "ack.socan"
    INGEST_DMP = "ingest.dmp"
    DISTRO_LABELGRID = "distro.labelgrid"
    CURVE_INGEST = "curve.ingest"
    TROLLEY_PAYOUT = "trolley.payout"
    PRO_MANUAL = "pro.manual"


class JobState(StrEnum):
    """RCMS Technical Spec v1.6, Section 5.5 -- state machine."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CHILD_PENDING = "child_pending"


class SplitStatus(StrEnum):
    """RCMS Technical Spec v1.6, Section 3.4 -- gates CWR eligibility (ADR-02)."""

    DRAFT = "draft"
    COMPLETE = "complete"
    REGISTERED = "registered"


class CompanyStatus(StrEnum):
    """RCMS Technical Spec v1.6, Section 3.1."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
