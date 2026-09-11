---
id: ADR-002
registry: rcms
title: pip and requirements.txt, not uv, for dependency management
status: accepted
date: 2026-09-04
tags: [dependencies, pip, uv, tooling]
supersedes: []
related: []
---

# ADR-002: pip and requirements.txt, not uv, for dependency management

## Context

The `init-django.sh` scaffolding convention this repo's structure was
partly adapted from (see ADR-001) uses `uv` for interpreter and
dependency management — `pyproject.toml` + `uv.lock`, pinned
`.python-version`, no direct `pip install`. This repo was already
built on plain `pip` + a virtualenv + `requirements.txt` before that
convention was known.

## Decision

Keep `pip`/`requirements.txt` for this repo rather than migrate to
`uv` mid-build. This is a deliberate choice made to avoid a toolchain
swap during an active build, not a rejection of `uv` on principle —
`uv`'s reproducibility guarantees (a real lockfile, pinned interpreter)
are genuine advantages `pip` alone doesn't have.

## Summary

This repo uses pip + requirements.txt, not uv, as a pragmatic choice
made mid-build rather than a considered rejection — left as an open
question for whether Octava standardizes on uv across Track B
services generally.

## Consequences

- No lockfile — `requirements.txt` pins exact versions by hand, which
  works but doesn't give the same reproducibility guarantee a real
  lockfile does.
- If Octava decides to standardize on `uv` across Track B services
  (RCMS, and whatever wraps the DMP vendor-clone), this repo is the
  one that would need migrating to match — worth doing before too many
  more Track B repos exist and the migration cost compounds.
- Not resolved here. This ADR exists so the decision is visible and
  revisitable, not so it's settled.
