"""
Job serializers implementing the n8n contract (RCMS Technical Spec v1.6,
Section 5): create Job -> run -> PATCH status.

This is the "api/" layer per the domain/adapters/api boundary: it
validates at the trust boundary and orchestrates, but the actual rules
-- idempotency-key computation, the PATCH allow-list, and state-
transition validation -- live in `domain/job_rules.py` and are called
from here, not reimplemented here. If a rule needs to change, change it
in domain/, not in this file.
"""

from rest_framework import serializers

from domain.job_rules import (
    PATCH_ALLOWED_FIELDS,
    WORKCASE_CACHE_FIELDS_PATCHABLE_VIA_JOB,
    compute_idempotency_key,
    is_valid_transition,
)

from core.models import Job


class JobDetailSerializer(serializers.ModelSerializer):
    """Read-only, full detail. Used for GET (spec 5.2 polling, and general inspection)."""

    class Meta:
        model = Job
        fields = "__all__"


class JobCreateSerializer(serializers.ModelSerializer):
    """
    POST /api/jobs/ (spec 5.1).

    `industry_id` is write-only and not stored directly -- it's one
    ingredient (alongside company, job_type, destination) that
    `domain.compute_idempotency_key` uses to compute `idempotency_key`.
    If a Job with the resulting key already exists, that existing Job
    is returned instead of creating a duplicate (spec 5.4).
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
        idempotency_key = compute_idempotency_key(
            company_id=validated_data["company"].id,
            job_type=validated_data["job_type"],
            destination=validated_data["destination"],
            industry_id=industry_id,
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

    `fields` is built directly from `domain.PATCH_ALLOWED_FIELDS` rather
    than a hand-copied list, so this serializer and the domain rule
    cannot silently drift apart -- if the allow-list changes in
    domain/job_rules.py, this serializer's writable fields change with
    it automatically.

    `validate()` additionally enforces the Section 5.5 state machine via
    `domain.is_valid_transition` -- a genuine improvement over the
    original slice, which accepted any state value without checking
    whether the transition made sense (e.g. queued -> succeeded,
    skipping running entirely, was previously accepted silently).

    Also accepts named write-only fields for the WorkCase-side of the
    allow-list (spec 5.3: n8n may write cached case flags on the Job's
    linked WorkCase, not just Job's own fields) -- currently just
    `work_case_cwr_registered`. This was documented in the spec from
    the start but missing from the original implementation; found by
    comparing against a parallel implementation that included it
    correctly. Adding another patchable WorkCase field means adding it
    to BOTH `domain.WORKCASE_CACHE_FIELDS_PATCHABLE_VIA_JOB` and a
    matching write-only field here -- the domain constant alone isn't
    enough to make a field reachable through this endpoint.
    """

    work_case_cwr_registered = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Job
        fields = list(PATCH_ALLOWED_FIELDS) + ["work_case_cwr_registered"]

    def validate(self, attrs):
        new_state = attrs.get("state")
        if new_state is not None and self.instance is not None:
            if not is_valid_transition(self.instance.state, new_state):
                raise serializers.ValidationError(
                    {
                        "state": (
                            f"Cannot transition from '{self.instance.state}' "
                            f"to '{new_state}' (spec Section 5.5)."
                        )
                    }
                )

        if "work_case_cwr_registered" in attrs:
            if self.instance is None or self.instance.work_case_id is None:
                raise serializers.ValidationError(
                    {
                        "work_case_cwr_registered": (
                            "This Job has no linked WorkCase -- nothing to update."
                        )
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        # WorkCase.cwr_registered is not a Job field -- pop it before
        # the normal ModelSerializer update handles Job's own fields,
        # then cascade it to the linked WorkCase separately.
        work_case_cwr_registered = validated_data.pop("work_case_cwr_registered", None)
        instance = super().update(instance, validated_data)

        if work_case_cwr_registered is not None:
            work_case = instance.work_case
            work_case.cwr_registered = work_case_cwr_registered
            work_case.save(update_fields=["cwr_registered", "updated_at"])

        return instance
