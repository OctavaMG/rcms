---
id: ADR-005
registry: rcms
title: WorkCase cache-flag cascade on Job PATCH
status: accepted
date: 2026-09-05
tags: [job, patch, workcase, cache, n8n]
supersedes: []
related: [rcms-research/design.md]
---

# ADR-005: WorkCase cache-flag cascade on Job PATCH

## Context

The Drive spec's Section 5.3 documented from the very first version
that n8n should be able to write "cached case flags (e.g.
`WorkCase.cwr_registered`, `ProductCase.distro_status`)" through the
Job PATCH endpoint — not just Job's own fields. The original
implementation of `JobPatchSerializer` only ever exposed Job's own six
fields (`state`, `external_ids`, `object_key`, `checksum`,
`n8n_run_id`, `error_text`) — the WorkCase-side half of the documented
contract was never actually built.

Found by comparing against a parallel implementation of the same
first-slice brief (a separate `rcms/` Django project inside the
`RCMS-Research` monorepo, `docs/design.md`), which included this
cascade correctly from the start: its documented PATCH allow-list
explicitly lists `cwr_sent`/`splits_complete` as patchable "cache
flags" alongside Job's own fields.

## Decision

Add `work_case_cwr_registered` as a write-only field on
`JobPatchSerializer`. If present in a PATCH request, it updates
`Job.work_case.cwr_registered` directly (not a `Job` model field
itself) after the normal Job field updates succeed. Rejected with 400
if the Job has no linked `work_case` — nothing to cascade to. The set
of WorkCase fields reachable this way lives in
`domain.WORKCASE_CACHE_FIELDS_PATCHABLE_VIA_JOB` (currently just
`cwr_registered`) — deliberately restricted to cache-Kind fields only
(see ADR-003). `WorkCase.split_status` (authority-Kind) must never be
added to this set.

## Summary

Fixes a real gap between the documented spec and the implementation:
n8n can now update WorkCase.cwr_registered (a cache-Kind flag) through
the same Job PATCH call, matching what the spec always said should be
possible. split_status remains completely unreachable through this
endpoint, proven by a dedicated test.

## Consequences

- `api/tests.py` covers three new cases: the cascade working with a
  linked WorkCase, rejection with no linked WorkCase, and confirmation
  that `split_status` stays unreachable even with the cascade in place.
- Adding another patchable WorkCase field (or the equivalent for
  `ProductCase` once it exists) requires updating **both**
  `domain.WORKCASE_CACHE_FIELDS_PATCHABLE_VIA_JOB` and adding a
  matching write-only field to the serializer — the domain constant
  alone doesn't make a field reachable through the API.
- This is the kind of gap the ADR rollup tool's cross-registry
  comparison is meant to surface faster than "read the other
  implementation's docs by hand, eventually."
