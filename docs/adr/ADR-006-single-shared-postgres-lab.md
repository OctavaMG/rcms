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
      -- the actual isolation boundary was open).
  - date: 2026-09-11
    note: >
      Added explicit GRANT ALL ON SCHEMA public step. On Postgres 15+
      (this instance runs 16), the public schema no longer grants CREATE
      to PUBLIC by default -- a security hardening change upstream. Without
      an explicit per-database grant, DMP's own `manage.py migrate` failed
      outright with "permission denied for schema public" trying to create
      django_migrations, even though the dmp role could connect and the
      REVOKE-based isolation above was correctly in place. Verified live
      on M80q002: migrations failed identically across five consecutive
      container restarts until this grant was added on M80q001, then all
      ten pending migrations applied cleanly on the next attempt. Both
      amendments are now part of the authoritative setup sequence below --
      the original database-creation steps were incomplete twice over.
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
isolation and the schema permissions are actually configured, not
assumed.** Two separate defaults caused real, live failures the first
time this was actually deployed rather than just designed on paper:
Postgres grants `CONNECT` on every newly created database to `PUBLIC`
by default (fixed by the first amendment above), and Postgres 15+
no longer grants `CREATE` on the `public` schema to `PUBLIC` by
default (fixed by the second). Both were missed in the original pass
at this ADR and caught only by actually running the deployment against
live hardware — see Amendments.

The lab currently has no load beyond local testing, and any
maintenance windows are coordinated manually by the one operator
running both boxes — the main cost of a shared instance (an M80q001
reboot taking DMP down too) is not a real risk under those conditions.

## Decision

**Lab:** one Postgres instance on M80q001. DMP gets its own database
within that instance (`dmp`, separate from `rcms`'s own database, no
shared schema, no cross-database queries, no default CONNECT access
to `rcms`, and explicit CREATE rights on its own `public` schema — see
setup steps below). M80q002 runs no local Postgres. DMP connects
across the LAN using the UFW path the bootstrap script already opened.

**This is explicitly a lab-resourcing decision, not a production
precedent.** Production topology (single managed instance vs. separate
instances vs. separate providers per system of record) is a distinct
decision to be made later against real infrastructure — most likely a
managed Postgres offering, where the availability/blast-radius
tradeoff that matters here (one box, one reboot, two outages) mostly
disappears because the provider handles HA and patching at the
instance level. Nothing here should be read as pre-deciding that
question. Managed Postgres offerings vary in which of these defaults
they preconfigure — don't assume either amendment below is unnecessary
just because the platform is managed; verify against whatever's
actually provisioned.

## Setup steps (on M80q001) — authoritative sequence

```bash
docker compose exec db psql -U rcms -c "CREATE DATABASE dmp;"
docker compose exec db psql -U rcms -c "CREATE USER dmp WITH PASSWORD '<pick a real password, not a guessable one>';"
docker compose exec db psql -U rcms -c "GRANT ALL PRIVILEGES ON DATABASE dmp TO dmp;"

# Required -- isolation. Without these, dmp can connect to rcms's
# database by default (PUBLIC CONNECT is granted automatically on
# every new database).
docker compose exec db psql -U rcms -c "REVOKE CONNECT ON DATABASE rcms FROM dmp;"
docker compose exec db psql -U rcms -c "REVOKE CONNECT ON DATABASE rcms FROM PUBLIC;"

# Required -- schema privileges. Without this, dmp can connect to its
# OWN database but Django's migrate command fails outright trying to
# create django_migrations ("permission denied for schema public").
# Must run against the dmp database specifically (-d dmp), not the
# default connection -- this is a per-database grant.
docker compose exec db psql -U rcms -d dmp -c "GRANT ALL ON SCHEMA public TO dmp;"
```

**Isolation check — confirm the boundary actually holds:**

```bash
docker compose exec db psql -U dmp -d dmp -c "\dt"    # expect: connects fine, empty (no tables yet)
docker compose exec db psql -U dmp -d rcms -c "\dt"   # expect: FATAL, permission denied for database "rcms"
```

If the second command connects successfully instead of failing — even
if it reports no tables found — the REVOKE steps were not applied
correctly. A successful connection with an empty result is not
evidence of isolation; only an explicit permission-denied failure is.

**Schema-privilege check — confirm migrations can actually run, don't
just assume the grant took:**

```bash
docker compose exec db psql -U dmp -d dmp -c "CREATE TABLE _adr006_check (id serial primary key); DROP TABLE _adr006_check;"
```

Should succeed silently. If this fails with "permission denied for
schema public," the `GRANT ALL ON SCHEMA public` step above either
wasn't run or was run against the wrong database.

## Consequences

- M80q002 stays lighter — no second Postgres instance competing with
  MinIO for memory/IO on a 16 GB box.
- One backup/restore procedure and one Postgres version to patch for
  the lab, not two.
- M80q002 now has a runtime dependency on M80q001 being up. Acceptable
  under current conditions (single operator, coordinated maintenance,
  no external load) — revisit if either of those conditions changes
  before a production topology decision is made.
- Isolation and schema-write access between `dmp` and `rcms` are not
  automatic on a shared instance — both require the explicit grants
  above. Any future role added to this same Postgres instance needs
  the same treatment (REVOKE CONNECT from other databases, GRANT ON
  SCHEMA public for its own), or it will silently fail at the exact
  moment its own migrations first try to run.

## Summary

Lab runs one Postgres instance on M80q001; DMP gets its own database
on it rather than a second instance on M80q002, using LAN access the
bootstrap script already opened. Chosen for lab resource/ops savings
under current no-load, single-operator conditions. Two separate
Postgres defaults had to be explicitly overridden before this actually
worked, each caught live rather than anticipated: PUBLIC's default
CONNECT privilege (isolation) and PUBLIC's no-longer-default CREATE
privilege on the public schema as of Postgres 15+ (migrations).
Explicitly scoped as a lab decision only — production Postgres
topology remains open and should be decided separately against real
(likely managed) infrastructure.
