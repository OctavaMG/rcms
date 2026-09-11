---
id: ADR-003
registry: rcms
title: Authority vs. cache field Kind classification
status: accepted
date: 2026-09-05
tags: [data-model, authority, cache, pointer, join, kind]
supersedes: []
related: [rcms-research/ADR-13]
---

# ADR-003: Authority vs. cache field Kind classification

## Context

`DATA-MODEL.md` classifies every Company/WorkCase/Job field by Kind
(authority / join / pointer / cache) — authority meaning RCMS owns the
value, cache meaning a copy that never triggers downstream logic, join
meaning a shared industry identifier, pointer meaning a reference to a
record another system owns. This was originally built with only
secondhand knowledge that a concept called "Kind" existed (via
`init-django.sh`'s template comment: "declare its Kind — ADR-13") with
no visibility into what that ADR actually said.

An inventory of the `RCMS-Research` monorepo (2026-09-05) surfaced the
actual file: `docs/decisions/ADR-13-authority-vs-cache.md`. Confirmed,
not just inferred: this is the genuine origin of the taxonomy already
in use here.

## Decision

Formally adopt the authority/join/pointer/cache Kind classification as
this repo's own decision, explicitly credited to its real source. Two
refinements pulled directly from the verified ADR-13 text, sharper
than this repo's original phrasing:

1. **Cache and pointer fields must never, by themselves, enqueue
   work** (CWR, ERN, payout, tax). Creating a Job stays an explicit,
   separate act (ADR-02, ADR-03) — a cache flag flipping true is never
   itself the trigger.
2. **`Job.state` is RCMS's authority *for that batch specifically* —
   not authority that the external vendor (MusicMark, LabelGrid,
   Curve, Trolley) actually accepted the underlying work or payment.**
   That distinction — batch-authority vs. vendor-truth — is cleaner
   than this repo's original note, which only said `state` was
   "gated by a real rule" without naming what the rule actually
   protects against.

## Summary

Adopts the authority/join/pointer/cache field-Kind taxonomy verified
against its real source, RCMS-Research's ADR-13-authority-vs-cache,
including two sharper refinements: cache/pointer fields never
self-trigger downstream work, and Job.state is batch-authority, not
vendor-truth.

## Consequences

- Every new model field added to `core/models.py` should get a Kind
  classification added to `DATA-MODEL.md` in the same change, per the
  Cursor rules already in place.
- `DATA-MODEL.md`'s note on `Job.state` should be updated to use the
  sharper "batch-authority, not vendor-truth" framing above.
- The source ADR also states (v1, this slice): "does not rename
  first-slice columns to `cached_*`" — matches this repo's own
  field naming (`cwr_registered`, not `cached_cwr_registered`) without
  either side having coordinated on it directly.
