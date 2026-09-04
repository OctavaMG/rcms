"""
core/ holds models, admin, and migrations only -- the Django ORM/
persistence layer. It has no business rules of its own to test.

- Domain rule tests (idempotency, PATCH allow-list, state transitions):
  domain/tests.py
- API contract tests (the actual HTTP behavior of /api/jobs/):
  api/tests.py
"""
