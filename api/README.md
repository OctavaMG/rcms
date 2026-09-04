# api/

DRF serializers, views, and routers for the n8n contract (RCMS
Technical Spec v1.6, Section 5).

This package is deliberately thin: it validates requests at the trust
boundary and wires HTTP verbs to model operations, but the actual
rules — idempotency-key computation, the PATCH allow-list, state-
transition validation — live in `domain/job_rules.py` and are called
from here, not reimplemented here. See `serializers.py` for exactly
where that handoff happens.

`api/tests.py` tests the HTTP contract end to end (auth, status codes,
request/response shape). `domain/tests.py` tests the underlying rules
in isolation, without any of this HTTP machinery.
