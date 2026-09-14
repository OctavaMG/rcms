"""
Job business rules. Pure functions and data -- no Django imports, no
database access. `api/serializers.py` calls into this module; it does
not reimplement these rules itself.

Three rules live here, each pulled directly from RCMS Technical Spec
v1.6:

1. `compute_idempotency_key` -- ADR-12 / spec Section 5.1. What makes a
   retried Job create safe rather than a duplicate.
2. `PATCH_ALLOWED_FIELDS` -- spec Section 5.3. The exact set of fields
   n8n/orchestration may ever write on a status update. This is the
   single source of truth for that list; `api/serializers.py`'s
   JobPatchSerializer builds its field list from this constant instead
   of hand-duplicating it, so the two cannot silently drift apart.
3. `is_valid_transition` -- spec Section 5.5's state machine, encoded
   as an actual enforced rule for the first time in this slice. The
   original first-cut of this code documented the state machine in the
   spec but never checked it in code -- nothing stopped a Job from
   jumping straight from `queued` to `succeeded`, or moving backwards
   from `succeeded` to `running`. This closes that gap while it's still
   cheap to close.
"""

from .types import JobState

PATCH_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "state",
        "external_ids",
        "object_key",
        "checksum",
        "n8n_run_id",
        "error_text",
    }
)
"""
Spec Section 5.3, verbatim: "n8n may only ever write state, external_ids,
cached case flags [not yet applicable in this slice -- no cache flags
live on Job itself], object_key, checksum, n8n_run_id, error text."

Anything not in this set represents a legal/business decision (shares,
WorkCase.split_status, company reassignment, etc.) and must never be
reachable through the n8n status-update contract, structurally --
not by a check someone could forget, but because the field simply
isn't in this set.
"""


VALID_STATE_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.RUNNING}),
    JobState.RUNNING: frozenset(
        {JobState.SUCCEEDED, JobState.FAILED, JobState.CHILD_PENDING}
    ),
    JobState.CHILD_PENDING: frozenset({JobState.SUCCEEDED, JobState.FAILED}),
    # SUCCEEDED and FAILED are terminal -- no outgoing transitions.
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
}
"""Spec Section 5.5's state machine, as an actual data structure."""


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """
    True if moving a Job from `from_state` to `to_state` is allowed by
    the spec's state machine (Section 5.5). A no-op "transition" (state
    unchanged -- e.g. n8n re-PATCHing the same status after a retried
    call) is always allowed, since that's normal idempotent behavior,
    not a state change.
    """
    if from_state == to_state:
        return True
    try:
        from_enum = JobState(from_state)
        to_enum = JobState(to_state)
    except ValueError:
        # Not a recognized state at all -- not this function's job to
        # say why; the caller's own field validation (choices=) handles
        # "is this a real state." This function only answers "is this
        # transition legal," so an unrecognized state is not "valid."
        return False
    return to_enum in VALID_STATE_TRANSITIONS.get(from_enum, frozenset())


def compute_idempotency_key(
    company_id: int, job_type: str, destination: str, industry_id: str = ""
) -> str:
    """
    ADR-12 / spec Section 5.1: "customer + job type + destination +
    industry id or operator batch id." Same inputs always produce the
    same key, which is what lets a retried Job create return the
    existing row instead of creating a duplicate (spec Section 5.4).
    """
    return ":".join([str(company_id), job_type, destination, industry_id or ""])


WORKCASE_CACHE_FIELDS_PATCHABLE_VIA_JOB: frozenset[str] = frozenset({"cwr_registered"})
"""
Spec Section 5.3: n8n may also write named cache-Kind flags on the
Job's linked WorkCase through the same PATCH call -- not just Job's
own fields (PATCH_ALLOWED_FIELDS above is the Job-side half of the
allow-list; this is the WorkCase-side half). This was documented in
the spec from the start but not actually implemented until this
revision -- a real gap found by comparing against a parallel
implementation's design.md, which included it correctly from the
start.

Only cache-Kind fields belong here (see DATA-MODEL.md /
rcms/docs/adr/ADR-003 for the Kind taxonomy). WorkCase.split_status is
authority, not cache, and must never be added to this set -- that's
the exact field this whole allow-list mechanism exists to protect.
"""
