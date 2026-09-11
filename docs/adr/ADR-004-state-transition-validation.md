---
id: ADR-004
registry: rcms
title: Job state-transition validation
status: accepted
date: 2026-09-04
tags: [job, state-machine, validation, patch, n8n]
supersedes: []
related: []
---

# ADR-004: Job state-transition validation

## Context

The n8n contract's state machine (RCMS Technical Spec, Section 5.5:
`queued → running → succeeded/failed`, `running → child_pending →
succeeded`) was documented from the first version of the spec but
never actually enforced in code — the original `PATCH` endpoint
accepted any `state` value without checking whether the transition
made sense. Nothing stopped a `PATCH` from moving a Job straight from
`queued` to `succeeded`, skipping `running` entirely, or moving
backwards from a terminal state.

## Decision

Add `domain.job_rules.is_valid_transition`, called from
`api/serializers.py`'s `JobPatchSerializer.validate()`, so an
out-of-order or backwards transition is rejected with `400` at the API
boundary rather than silently accepted. A same-state "transition" (the
new value equals the current value) is always allowed, since that's
normal idempotent behavior — n8n re-sending an unchanged status after
a retried HTTP call, not an actual state change.

## Summary

Adds real enforcement of the documented Section 5.5 state machine —
Job.state transitions are now validated against an explicit
from-state/to-state rule table, rejecting invalid transitions (e.g.
queued straight to succeeded) with 400 instead of accepting any value.

## Consequences

- `api/tests.py:test_patch_rejects_invalid_state_transition` and
  `test_patch_allows_valid_transition` cover this directly; the rule
  itself is separately unit-tested in `domain/tests.py` without any
  HTTP machinery.
- If the spec's state machine ever changes (e.g. a new state is
  added), `domain.job_rules.VALID_STATE_TRANSITIONS` is the one place
  to update — the API layer doesn't hardcode the rule itself.
