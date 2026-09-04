# RCMS — first Django slice (AgentSpecd-structured)

Open Item 2 from `Octava_RCMS_Technical_Spec_v1.6.md`: Company + WorkCase +
Job + Admin + token API. This is code — it belongs in git, not Drive, per
Octava's own dev/ops governance discussion: Drive holds the spec (the
decision record); this repo holds the implementation, and git's commit
history is the audit trail for how the implementation evolves.

**Structure note (2026-09-04):** this project was originally a flat
Django app (`core/` holding models, serializers, views, and business
logic together). It's been restructured into the `domain/` /
`adapters/` / `api/` layering described in `.cursor/rules/agentspecd.mdc`
— retrofitted from a parallel effort's `init-django.sh` conventions,
done deliberately while the codebase was still small enough for it to
be cheap. See `DESIGN.md` and `DATA-MODEL.md` for the filled-in
contracts (not generic templates — they describe RCMS's actual
Company/WorkCase/Job entities).

## Layout

```
core/       Django ORM layer only — models.py, admin.py, migrations/.
            No business rules live here.
domain/     Pure Python. No Django imports. The actual rules:
            idempotency-key computation, the PATCH allow-list, and
            Job state-transition validation. domain/tests.py runs
            without a database.
api/        DRF serializers, views, urls. Thin — calls into domain/
            for rules rather than containing them. api/tests.py
            tests the real HTTP contract end to end.
adapters/   Empty in this slice (README describes what lands here
            later: MinIO, DMP, MusicMark, LabelGrid, Curve, Trolley
            clients — Open Items 3-6).
```

## What's in this slice, and what's deliberately not

**In:** `Company` (spec §3.1), `WorkCase` (spec §3.4), `Job` (spec §3.7),
Django Admin for all three, and the full n8n contract from spec §5:

- `POST /api/jobs/` — idempotent create (§5.1)
- `GET /api/jobs/?state=queued` — n8n polling (§5.2)
- `PATCH /api/jobs/{id}/` — status update, allow-list **and** state-machine
  enforced (§5.3, §5.5 — the state-machine check is new as of this
  restructure; the original slice accepted any state value without
  checking whether the transition was legal)
- `POST /api-token-auth/` — exchange username/password for a token

**Deliberately out** (see `DESIGN.md` §4 for the full non-goals list):
`Person`, `Engagement`, `ProductCase`, `RecordingLink`, `Job.product_case`,
any real `adapters/` integration code, a `Company` API endpoint (Admin
only, for now).

## The two rules worth understanding before touching this code

**The PATCH allow-list** (`domain/job_rules.py:PATCH_ALLOWED_FIELDS`) is
the single source of truth for what n8n may ever write on a status
update. `api/serializers.py`'s `JobPatchSerializer` builds its field
list *from* this constant rather than hand-duplicating it — change the
rule in one place, the enforcement follows automatically.

**State-transition validation** (`domain/job_rules.py:is_valid_transition`)
now actually enforces the state machine the spec has documented since
v1.0 (§5.5) but no code checked until this restructure. A `PATCH` that
tries to skip straight from `queued` to `succeeded` is rejected with
400 — see `api/tests.py:test_patch_rejects_invalid_state_transition`.

Both are tested twice, deliberately: once in `domain/tests.py` in
complete isolation (no Django test DB, no HTTP), and once in
`api/tests.py` as a full HTTP round trip, so a bug in either the rule
itself or in how the API layer wires it up gets caught.

## Running it

### Quick local check (sqlite, no Docker)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DB_ENGINE=sqlite3
python manage.py migrate
python manage.py test domain api    # 20 tests
python manage.py createsuperuser
python manage.py runserver
```

### Real deployment (M80q001, Docker Compose — Postgres + n8n)

```bash
cp .env.example .env               # fill in real SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Admin: `http://192.168.0.81:8000/admin/`
API token: `POST http://192.168.0.81:8000/api-token-auth/` with
`{"username": "...", "password": "..."}`

Ports (8000, 5432, 5678) already match what `octava-lab-bootstrap.sh`
opened in UFW for the `ops` role — nothing further to open.

## Verification done before handoff

`manage.py check` clean, migrations apply cleanly from a fresh
database, and all 20 tests pass across `domain/` and `api/` — including
the new state-transition rejection test, and the `DomainEnumSyncTests`
that guard against `domain/types.py` and `core/models.py`'s Django
`TextChoices` silently drifting apart.

## Next steps (per spec Open Items)

3. Vendor-clone DMP as a real `git clone`/submodule (ADR-11 — not a
   flat copy), first real batch = a `cwr.musicmark` Job with a file
   landing in MinIO. This is also the first real `adapters/` code —
   `adapters/dmp_client.py` and/or `adapters/minio_client.py`.
4. This slice already covers the DRF endpoints from Open Item 4 —
   remaining piece is an actual n8n workflow calling them for real.
