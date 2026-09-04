from django.contrib import admin

from .models import Company, Job, WorkCase


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "billing_email", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "legal_name", "billing_email"]


@admin.register(WorkCase)
class WorkCaseAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "iswc", "split_status", "cwr_registered"]
    list_filter = ["split_status", "cwr_registered"]
    search_fields = ["title", "iswc", "dmp_work_id"]
    autocomplete_fields = ["company"]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["id", "job_type", "destination", "state", "company", "created_at"]
    list_filter = ["job_type", "state", "destination"]
    search_fields = ["idempotency_key", "n8n_run_id", "object_key"]
    autocomplete_fields = ["company", "work_case", "parent_job"]
    readonly_fields = ["idempotency_key", "created_at", "updated_at"]
