# DESIGN.md

> Source-of-truth product and experience contract.
> Humans and any AI tooling (Cursor, agents) must treat this as authoritative
> for surfaces, flows, and scope. Data shape and storage rules live in
> DATA-MODEL.md. The full spec this contract is derived from:
> `Octava_RCMS_Technical_Spec_v1.6.md` (Drive, 01_Brands/RCMS).

## 1. Product Summary

RCMS (Rights & Case Management System) is Octava's internal operations
backend for managing music-publishing customer relationships, composition
cases, and the batch jobs that move data to external registration and
distribution systems (MusicMark, the MLC, LabelGrid, Curve, Trolley) and
to the vendored publishing-catalogue engine (Django Music Publisher /
DMP). It is not a customer-facing product — it's the "operations desk"
internal staff use to track who Octava works with, what compositions
are in Octava's care, and what's happened (or is happening) to move
those compositions through registration and distribution.

RCMS is the system of record for **customers, cases, and job status**.
It is deliberately *not* the system of record for legal shares, CWR/ERN
bytes, or royalty math — those stay with DMP and Curve respectively.
See Section 2 of the spec ("Systems of Record") for the full table.

## 2. Stack declaration

Internal service — Architecture v3.1 Track B (Section 6B). Django 5.2
(pinned `>=5.2,<5.3`, ADR-11), chosen independently and converged upon
twice: Architecture v3.1's own two-track decision, and RCMS-Research's
separate ADR-14 ("Django internal, TypeScript external") — same
conclusion, reached by two different efforts. See RCMS Technical Spec
v1.6, Section 9.5 for the reconciliation note on that.

- Staff UI: Django Admin. No custom staff SPA (explicit non-goal, spec
  Section 7).
- Machine interface: Django REST Framework, token authentication. This
  is the *only* documented contract other systems (n8n, and later
  webhooks) may call against RCMS — see spec Section 5.
- Dependency management: `pip` + `requirements.txt` inside a
  virtualenv, not `uv`. This was a deliberate choice for this slice to
  avoid introducing a new toolchain mid-build; revisit if Octava
  standardizes on `uv` across Track B services (a real possibility,
  worth a decision but not made here — see Open Item 8 territory).

## 3. Surfaces

- **Django Admin** (`/admin/`): Company, WorkCase, Job — list/detail/
  edit screens for internal ops staff. This is the v1 operations desk
  in full; there is no other staff-facing UI in this slice.
- **API** (`/api/`, token-authenticated):
  - `POST /api/jobs/` — create a Job (idempotent — spec 5.1)
  - `GET /api/jobs/?state=queued` — n8n polling for pickup (spec 5.2)
  - `PATCH /api/jobs/{id}/` — status update, allow-list + state-machine
    enforced (spec 5.3, 5.5)
  - `POST /api-token-auth/` — exchange username/password for a token
- **No customer-facing surface.** The Strapi customer portal (spec's
  ADR-10, "portal last") ships only after an internal Job completes
  end-to-end — not in scope for this or any near-term slice.

## 4. Non-Goals

Pulled directly from RCMS Technical Spec v1.6, Section 7 — do not
reopen these without a spec change:

- Twenty / Django CRM / SaaS Pegasus as the system of record
- Generating ERN inside RCMS or DMP
- Auto-CWR when a DSP delivery completes (CWR is explicit — ADR-02)
- SSO in the lab
- Custom staff SPA — Django Admin is the staff UI
- Multi-operator SaaS tenancy — one RCMS install, many Company customers
- DDEX libraries inside RCMS
- Merging DMP and RCMS into one process
- RabbitMQ or Celery on day one

Additionally, out of scope for *this specific slice* (not rejected —
just sequenced later, per Open Item 2's own definition):

- `Person`, `Engagement`, `ProductCase`, `RecordingLink` (spec Sections
  3.2, 3.3, 3.5, 3.6)
- Any real integration code in `adapters/` — MinIO, DMP, MusicMark,
  LabelGrid, Curve, Trolley clients. This slice's job is to give those
  something (the Job model + API) to write to, not to build them.
