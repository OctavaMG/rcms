# adapters/

Integrations with systems RCMS does not own. Empty in this slice —
nothing calls out to an external system yet — but this is where the
following land as they're built (RCMS Technical Spec v1.6, Open Items
3–6):

- `minio_client.py` — object storage for CWR/ACK/EBR files (Job.object_key)
- `n8n_client.py` — if RCMS ever needs to call n8n directly rather than
  only being called by it (not currently required — n8n polls/receives
  webhooks per spec Section 5.2, RCMS doesn't initiate)
- `dmp_client.py` — DMP Admin/CSV ingest (ADR-08: DMP's REST API is
  read-only in v1)
- Future: MusicMark SFTP, LabelGrid REST (ADR-09), Curve, Trolley

Each adapter implements an interface `domain/` defines — nothing
outside this package should import a vendor SDK directly. `api/` and
`core/` reach external systems through here, not around it.
