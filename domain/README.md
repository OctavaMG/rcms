# domain/

Pure domain types and business rules for RCMS. No Django imports, no
database access — everything here is importable and testable with
nothing but the Python standard library (`domain/tests.py` proves it,
via plain `unittest`, not Django's test client).

- `types.py` — canonical string vocabulary (`JobType`, `JobState`,
  `SplitStatus`, `CompanyStatus`). Django's own `TextChoices` classes in
  `core/models.py` are asserted to match these value-for-value in
  `domain/tests.py`'s `DomainEnumSyncTests` — change one, you must
  change (and re-verify) the other.
- `job_rules.py` — the actual rules: idempotency-key computation
  (ADR-12), the PATCH allow-list (spec Section 5.3), and Job
  state-transition validation (spec Section 5.5).

`api/` calls into here. It does not reimplement these rules itself —
if you find yourself writing idempotency-key logic or a status
allow-list anywhere in `api/` or `core/`, that logic belongs here
instead, and `api/` should import and call it.
