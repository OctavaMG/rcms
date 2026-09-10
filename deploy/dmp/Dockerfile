# DMP (django-music-publisher) — vendored per ADR-11.
#
# This Dockerfile lives at rcms/deploy/dmp/Dockerfile but is NOT built
# from this directory. docker-compose.dmp.yml (same folder) sets the
# build context to ../../django-music-publisher -- the submodule --
# and points here for the Dockerfile itself. Building from this
# directory directly (e.g. `docker build .`) will fail; use the
# compose file.
#
# Base pinned to match the submodule's own runtime.txt (python-3.12.4)
# at the pinned commit, not a floating "3.12" tag.
FROM python:3.12.4-slim AS base

ARG DMP_COMMIT=4fdec3d1afbc4deef2507f804e31b25cfcf9dbf8
LABEL org.octava.dmp.vendor-commit=$DMP_COMMIT
LABEL org.octava.dmp.vendor-branch=26.4
LABEL org.octava.dmp.vendor-source=OctavaMG/django-music-publisher
LABEL org.octava.dmp.adr=ADR-11

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 dmp && chown -R dmp:dmp /app
USER dmp

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001

EXPOSE 8001

# Matches the submodule's own Procfile web process (waitress, not
# manage.py runserver).
CMD ["sh", "-c", "python manage.py migrate --noinput && waitress-serve --host=0.0.0.0 --port=$PORT dmp_project.wsgi:application"]
