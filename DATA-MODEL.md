# DATA-MODEL.md

> Source of truth for data this system collects or stores and the rules
> that govern it. Physical implementation lives in `core/models.py` and
> migrations. Do not invent tables, fields, or relationships that are
> not listed here — if `core/models.py` and this file ever disagree,
> that's a bug in one of them.

## 1. Overview

Three entities in this slice: `Company` (the customer), `WorkCase` (a
composition in Octava's care), and `Job` (one batch sent to or received
from an external system). Full field-by-field detail, including
django-idiomatic types, lives in RCMS Technical Spec v1.6 Section 3 —
this document adds the **Kind** classification that spec doesn't
carry, since that's a code-adjacent governance concern rather than a
product-spec one.

## 2. Entities / Data Contracts

**Kind**, per field:
- **authority** — RCMS owns this value; it's the decision, not a copy of one
- **join** — a shared identifier (ISWC, ISRC, UPC/EAN, IPI) used to
  correlate records across systems (ADR-01)
- **pointer** — a reference to a record owned by a different system
- **cache** — a copy for display/verification; writing it never
  triggers downstream business logic, and it is never itself the
  source of truth

### Company

| Field | Type | Kind | Notes |
|---|---|---|---|
| `name` | CharField | authority | |
| `legal_name` | CharField | authority | |
| `billing_email` | EmailField | authority | |
| `status` | CharField (choices) | authority | |
| `notes` | TextField | authority | |
| `created_at` / `updated_at` | DateTimeField | authority | System-managed, still RCMS-owned |

### WorkCase

| Field | Type | Kind | Notes |
|---|---|---|---|
| `company` | FK → Company | authority | Internal FK — both ends owned by RCMS |
| `title` | CharField | authority | |
| `iswc` | CharField | join | ADR-01 — populated once registered externally |
| `dmp_work_id` | CharField | pointer | References a record DMP owns |
| `split_status` | CharField (choices) | **authority** | The business-critical field — gates CWR eligibility (ADR-02). This is exactly the kind of field the Job PATCH allow-list exists to keep n8n away from. |
| `cwr_registered` | BooleanField | cache | Explicitly documented as a cached flag — source of truth is DMP/society ACKs, not RCMS |
| `notes` | TextField | authority | |

### Job

| Field | Type | Kind | Notes |
|---|---|---|---|
| `company` | FK → Company | authority | Internal FK |
| `job_type` | CharField (choices) | authority | |
| `destination` | CharField | authority | |
| `state` | CharField (choices) | authority* | *See note below — Job.state is a workflow status, not a legal/business decision, which is why n8n is allowed to write it through the PATCH contract while WorkCase.split_status never is. |
| `object_key` | CharField | pointer | References an object MinIO owns |
| `checksum` | CharField | cache | Verification copy, not authoritative content |
| `n8n_run_id` | CharField | pointer | References an execution n8n owns |
| `external_ids` | JSONField | pointer | Society/vendor-side IDs, by definition |
| `error_text` | TextField | authority | RCMS's own record |
| `idempotency_key` | CharField | authority | RCMS-computed (domain/job_rules.py), RCMS-owned |
| `parent_job` | FK → Job (self) | authority | Internal FK |
| `work_case` | FK → WorkCase | authority | Internal FK |

**Note on `Job.state` as "authority\*":** unlike `WorkCase.split_status`
(a legal/business decision only RCMS's own domain logic may change),
`Job.state` is RCMS's authoritative record of a workflow's progress —
but the spec's own contract (Section 5) deliberately lets an external
system (n8n) advance it, *through a defined, validated contract*
(`domain.is_valid_transition`), not through free-form access. The
distinction that actually matters isn't "who's allowed to write it" —
it's "is writing it gated by a real rule, or open." `state` is gated
by the state machine; `split_status` isn't reachable through this
contract at all. Cache/pointer fields (`checksum`, `object_key`,
`external_ids`, `n8n_run_id`) are the fields where n8n has essentially
unrestricted write access, because writing them never triggers a
business decision on its own.

## 3. Cross-Cutting Rules

- Timestamps: UTC, Django's `auto_now_add`/`auto_now` (spec doesn't
  currently need timezone-aware business logic beyond storage).
- No soft-delete in this slice — `on_delete=PROTECT` on Company FKs
  prevents deleting a Company with existing cases/jobs; `parent_job`
  cascades (deleting a parent Job's record deletes its child ACK
  Jobs); `work_case` on Job is `SET_NULL` (deleting a WorkCase doesn't
  erase Job history).
- Identifiers: no invented universal work/release id (ADR-01). Foreign
  ids are pointers (`dmp_work_id`), never adopted as RCMS's own primary
  key for a concept another system owns.

## 4. System of Record

Full table in RCMS Technical Spec v1.6, Section 2. Summary for the
entities in this slice: RCMS is SoR for Company/WorkCase/Job identity
and status. DMP is SoR for the actual publishing catalogue (splits,
CWR bytes). Neither this file nor `core/models.py` should ever try to
become the source of truth for something DMP, Curve, or Trolley owns.

## 5. Explicitly Out of Scope

`Person`, `Engagement`, `ProductCase`, `RecordingLink` (spec Sections
3.2, 3.3, 3.5, 3.6), and `Job.product_case` (can't exist until
`ProductCase` does — see the comment in `core/models.py` for where to
add it). Not forgotten — sequenced into a later slice per Open Item 2's
own defined scope.
