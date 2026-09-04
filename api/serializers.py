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

from domain.job_rules import PATCH_ALLOWED_FIELDS, compute_idempotency_key, is_valid_transition

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
    """

    class Meta:
        model = Job
        fields = list(PATCH_ALLOWED_FIELDS)

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
        return attrs
