"""
API views for the n8n contract (spec Section 5).

This is the one documented contract other systems (n8n, and later
webhooks) may call against RCMS (ADR-03 / Architecture v3.1 Section 6B).
No other endpoints exist in this slice, and no undocumented ones should
be added later without updating the spec first.
"""

from rest_framework import generics, permissions

from core.models import Job
from .serializers import JobCreateSerializer, JobDetailSerializer, JobPatchSerializer


class JobListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/jobs/?state=queued   -- n8n polling for pickup (spec 5.2).
    POST /api/jobs/                -- create a Job (spec 5.1), idempotent.
    """

    queryset = Job.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return JobCreateSerializer
        return JobDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        state = self.request.query_params.get("state")
        if state:
            qs = qs.filter(state=state)
        return qs


class JobDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/jobs/{id}/  -- full detail.
    PATCH /api/jobs/{id}/  -- status update (spec 5.3), allow-list enforced
                              by JobPatchSerializer's field list.

    No PUT: only PATCH is permitted, since a full-object replace has no
    place in this contract -- n8n updates status fields, it doesn't
    resubmit the whole Job.
    """

    queryset = Job.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return JobPatchSerializer
        return JobDetailSerializer
