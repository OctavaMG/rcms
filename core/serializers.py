"""
Job serializers implementing the n8n contract (RCMS Technical Spec v1.6,
Section 5): create Job -> run -> PATCH status.

Two deliberately separate serializers for Job, not one shared one:

- JobCreateSerializer: what RCMS/n8n may send on POST (spec 5.1).
- JobPatchSerializer: what n8n may send on PATCH (spec 5.3) -- and *only*
  that. The PATCH allow-list from the spec (state, external_ids,
  object_key, checksum, n8n_run_id, error_text) is enforced structurally
  here by simply not including any other field in `fields`. DRF silently
  ignores extra keys in a PATCH body that aren't in the serializer's
  field list, so a caller cannot smuggle a write to e.g. idempotency_key,
  company, or (once it exists) WorkCase.split_status through this
  endpoint -- not because of a runtime check that could be forgotten,
  but because the field simply isn't reachable from here.

JobDetailSerializer is read-only, for GET (n8n polling, spec 5.2, and
general inspection) -- exposes everything.
"""

from rest_framework import serializers

from .models import Job


class JobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"


class JobCreateSerializer(serializers.ModelSerializer):
    """
    POST /api/jobs/ (spec 5.1).

    `industry_id` is write-only and not stored directly -- it's one
    ingredient (alongside company, job_type, destination) in computing
    `idempotency_key` server-side, per ADR-12 / spec 5.1. If a Job with
    the resulting idempotency_key already exists, that existing Job is
    returned instead of creating a duplicate -- this is what makes
    n8n's create-on-retry behavior safe (spec 5.4).
    """

    industry_id = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default="",
        help_text="ISWC/ISRC/UPC/batch id -- used only to compute "
                  "idempotency_key, not stored as its own column.",
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "company",
            "job_type",
            "destination",
            "work_case",
            "parent_job",
            "object_key",
            "industry_id",
            "state",
            "idempotency_key",
        ]
        read_only_fields = ["id", "state", "idempotency_key"]

    def create(self, validated_data):
        industry_id = validated_data.pop("industry_id", "")
        idempotency_key = ":".join(
            [
                str(validated_data["company"].id),
                validated_data["job_type"],
                validated_data["destination"],
                industry_id,
            ]
        )

        existing = Job.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

        validated_data["idempotency_key"] = idempotency_key
        validated_data.setdefault("state", Job.State.QUEUED)
        return Job.objects.create(**validated_data)


class JobPatchSerializer(serializers.ModelSerializer):
    """
    PATCH /api/jobs/{id}/ (spec 5.3) -- the n8n status-update contract.

    This is the PATCH allow-list from the spec, enforced by field
    inclusion. Do not add fields here without checking spec Section 5.3
    first -- anything added becomes writable by n8n/orchestration, which
    is exactly the boundary this serializer exists to hold.
    """

    class Meta:
        model = Job
        fields = [
            "state",
            "external_ids",
            "object_key",
            "checksum",
            "n8n_run_id",
            "error_text",
        ]
