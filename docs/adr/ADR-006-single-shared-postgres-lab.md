---
id: ADR-006
registry: rcms
title: Single shared Postgres instance for the lab (DMP + RCMS)
status: accepted
date: 2026-09-10
tags: [postgres, database, lab, infrastructure, dmp, topology]
supersedes: []
related: [ADR-11, ADR-01]
amendments:
  - date: 2026-09-11
    note: >
      Added explicit REVOKE CONNECT step. GRANT ALL PRIVILEGES ON DATABASE
      dmp TO dmp only grants rights on the dmp database itself -- it does
      not restrict the dmp role's default PUBLIC CONNECT privilege on
      other databases on the same instance (rcms included). Verified live
      on M80q001: without the REVOKE, `psql -U dmp -d rcms` connected
      successfully (found no tables, but the connection itself succeeded
      -- the actual isolation boundary was open). The original database-
      creation steps below were incomplete; this amendment is now the
      authoritative version.
---

# ADR-006: Single shared Postgres instance for the lab (DMP + RCMS)

## Context

M80q001 (`ops` role) already runs Postgres as part of the RCMS stack.
M80q002 (`engines` role) runs DMP + MinIO, and DMP needs a Postgres
database of its own. The open question, raised during the DMP
vendor-clone work (ADR-11): should M80q002 run its own local Postgres
instance, matching the bootstrap script's per-machine role isolation,
or should DMP connect across the LAN to the existing instance on
M80q001 as a separate database?

`octava-lab-bootstrap.sh` already anticipated the shared-instance path
— its UFW rule for the `ops` role scopes Postgres (5432) to the whole
lab subnet, not just localhost, specifically so a box in the `engines`
role could reach it. That groundwork existed before this ADR, unused
until now.

Postgres enforces database-level isolation on its own: two databases
on the same instance cannot be joined across each other without
`dblink`/`postgres_fdw`. Sharing one instance is therefore a hardware
and uptime decision, not a data-coupling risk — **provided the
isolation is actually configured, not assumed.** Postgres grants
`CONNECT` on every newly created database to the `PUBLIC` role by
default. A role created for one database (e.g. `dmp`) can connect to
every other database on the same instance (e.g. `rcms`) unless that
default is explicitly revoked. This was missed in the first pass at
this ADR and caught only when the isolation check below was actually
run against a live instance — see Amendment, 2026-09-11.

The lab currently has no load beyond local testing, and any
maintenance windows are coordinated manually by the one operator
running both boxes — the main cost of a shared instance (an M80q001
reboot taking DMP down too) is not a real risk under those conditions.

## Decision

**Lab:** one Postgres instance on M80q001. DMP gets its own database
within that instance (`dmp`, separate from `rcms`'s own database, no
shared schema, no cross-database queries, **and no default CONNECT
access to `rcms` either** — see setup steps below). M80q002 runs no
local Postgres. DMP connects across the LAN using the UFW path the
bootstrap script already opened.

**This is explicitly a lab-resourcing decision, not a production
precedent.** Production topology (single managed instance vs. separate
instances vs. separate providers per system of record) is a distinct
decision to be made later against real infrastructure — most likely a
managed Postgres offering, where the availability/blast-radius
tradeoff that matters here (one box, one reboot, two outages) mostly
disappears because the provider handles HA and patching at the
instance level. Nothing here should be read as pre-deciding that
question.

## Setup steps (on M80q001)

```bash
docker compose exec db psql -U rcms -c "CREATE DATABASE dmp;"
docker compose exec db psql -U rcms -c "CREATE USER dmp WITH PASSWORD '<pick a real password, not a guessable one>';"
docker compose exec db psql -U rcms -c "GRANT ALL PRIVILEGES ON DATABASE dmp TO dmp;"

# Required -- do not skip. Without these two REVOKEs, the dmp role can
# connect to rcms's database by default (PUBLIC CONNECT is granted
# automatically on every new database). This is the step the original
# version of this ADR omitted.
docker compose exec db psql -U rcms -c "REVOKE CONNECT ON DATABASE rcms FROM dmp;"
docker compose exec db psql -U rcms -c "REVOKE CONNECT ON DATABASE rcms FROM PUBLIC;"
```

**Isolation check — confirm the boundary actually holds, don't just
assume the grants worked:**

```bash
docker compose exec db psql -U dmp -d dmp -c "\dt"    # expect: connects fine, empty (no tables yet)
docker compose exec db psql -U dmp -d rcms -c "\dt"   # expect: FATAL, permission denied for database "rcms"
```

If the second command connects successfully instead of failing — even
if it reports no tables found — the REVOKE steps were not applied
correctly. A successful connection with an empty result is not
evidence of isolation; only an explicit permission-denied failure is.

## Consequences

- M80q002 stays lighter — no second Postgres instance competing with
  MinIO for memory/IO on a 16 GB box.
- One backup/restore procedure and one Postgres version to patch for
  the lab, not two.
- M80q002 now has a runtime dependency on M80q001 being up. Acceptable
  under current conditions (single operator, coordinated maintenance,
  no external load) — revisit if either of those conditions changes
  before a production topology decision is made.
- Isolation between `dmp` and `rcms` is not automatic on a shared
  instance — it requires the explicit `REVOKE CONNECT` steps above.
  Any future role added to this same Postgres instance needs the same
  treatment, or it will default to being able to connect to every
  existing database on the instance.

## Summary

Lab runs one Postgres instance on M80q001; DMP gets its own database
on it rather than a second instance on M80q002, using LAN access the
bootstrap script already opened. Chosen for lab resource/ops savings
under current no-load, single-operator conditions. Isolation between
databases requires explicitly revoking PUBLIC's default CONNECT
privilege — verified live on 2026-09-11 after an initial pass missed
this and a role was found able to connect to a database it shouldn't
have. Explicitly scoped as a lab decision only — production Postgres
topology remains open and should be decided separately against real
(likely managed) infrastructure.
