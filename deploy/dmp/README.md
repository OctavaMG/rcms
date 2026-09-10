# deploy/dmp/

Deployment scaffolding for the DMP submodule (`rcms/django-music-publisher`,
pinned to `4fdec3d1afbc4deef2507f804e31b25cfcf9dbf8` on the `26.4` branch,
verified via a fresh clone — see ADR-11). Deliberately kept out of the
submodule itself so DMP's own repo stays a clean, diffable copy of
upstream.

## Already verified (no need to re-check)

- `setup.py`/`requirements.txt` agree on `Django>=5.2,<5.3` at this
  commit — the mismatch on `master` is fixed here.
- DMP's REST API is genuinely read-only (`ReadOnlyModelViewSet`
  throughout `api.py`) and Admin has a real CSV import/export path —
  confirms ADR-08's ingest-path assumption directly in code.
- DMP already ships `django-storages` + `boto3`, reading all S3 config
  from env vars — pointing it at MinIO needs zero code changes.

## Before first `docker compose up` here

1. **Create the `dmp` database on M80q001.** Commands and an
   isolation check are in `rcms/docs/adr/ADR-005-single-shared-postgres-lab.md`.
   Don't skip the isolation check — confirms the `dmp` role can't see
   `rcms`'s own tables before you trust the separation.

2. **Copy `.env.dmp.example` to `.env.dmp` and fill it in** —
   `MINIO_ROOT_USER`/`PASSWORD`, a real `DMP_SECRET_KEY`
   (`python3 -c "import secrets; print(secrets.token_urlsafe(50))"`),
   and `DMP_DATABASE_URL` with the password matching what you set for
   the `dmp` Postgres role.

3. **Confirm you're running this from `rcms/deploy/dmp/`**, not
   copied elsewhere — the build context (`../../django-music-publisher`)
   and Dockerfile path (`../deploy/dmp/Dockerfile`) are both relative
   and will break if this folder moves independently of the repo.

## Bring it up

```bash
cd rcms/deploy/dmp
docker compose -f docker-compose.dmp.yml --env-file .env.dmp up -d --build
docker compose -f docker-compose.dmp.yml logs -f dmp
```

Migrations run automatically on container start. Watch for a clean
`waitress-serve` startup line, no traceback.

## Verify after it's up

- Create the `rcms` bucket in the MinIO console (`:9001`) — DMP won't
  create it for you.
- `docker compose -f docker-compose.dmp.yml exec dmp python manage.py createsuperuser`,
  then confirm `:8001/admin/` logs in and `OPTION_FILES` shows as
  S3-backed rather than falling back to local disk.

## Still open after this

- **First real batch** — land catalogue data via Admin/CSV, run
  `generatecwr`, get the resulting file into RCMS's own
  `rcms/{customer}/{job_id}/out/...` MinIO key as the first real
  `cwr.musicmark` Job. Separate step once DMP itself is confirmed
  running clean.
