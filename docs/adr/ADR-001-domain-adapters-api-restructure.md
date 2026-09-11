---
id: ADR-001
registry: rcms
title: Restructure into domain/adapters/api layering
status: accepted
date: 2026-09-04
tags: [structure, domain, adapters, api, django]
supersedes: []
related: []
---

# ADR-001: Restructure into domain/adapters/api layering

## Context

The first working slice (Company + WorkCase + Job + Admin + token API)
was originally a flat Django app: models, serializers, views, and the
actual business rules (idempotency-key computation, the PATCH
allow-list) all lived together in one `core/` app. It worked and was
fully tested, but business logic and Django/DRF plumbing weren't
separable — testing a rule meant going through the HTTP layer even
when the rule itself had nothing to do with HTTP.

Separately, a parallel effort (`init-django.sh`, an AgentSpecd
scaffolding script) surfaced the same day, encoding a
`domain`/`adapters`/`api` boundary convention: pure business rules with
zero Django imports, external integrations behind an adapter
interface, and a thin API layer that calls into both rather than
containing logic itself.

## Decision

Retrofit that layering onto the existing slice while it was still
small (three models, one API contract) rather than defer it until
DMP/MusicMark/Curve/Trolley integrations made the change expensive.
`core/` now holds only the Django ORM layer (models, admin,
migrations). `domain/` holds pure Python rules with no Django imports —
idempotency-key computation, the PATCH allow-list, and Job
state-transition validation (see ADR-004). `api/` is a thin DRF layer
that calls into `domain/` rather than reimplementing its rules.
`adapters/` is an empty placeholder for the vendor integrations that
don't exist yet.

## Summary

Restructured the existing Django slice into domain/adapters/api
layering (pure business rules separated from Django/DRF plumbing),
adapted from the parallel init-django.sh/AgentSpecd scaffolding
convention, done deliberately while the codebase was still small.

## Consequences

- `domain/tests.py` runs with no database and no Django test client —
  faster, and proof the rules really don't depend on the framework.
- Adding the next vendor integration (DMP, MusicMark) has an obvious
  home (`adapters/`) rather than another ad hoc client class dropped
  into whatever file seemed convenient.
- One deliberate deviation from the source template: dependency
  management stayed `pip`/`requirements.txt` rather than switching to
  `uv` — see ADR-002.
