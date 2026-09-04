from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # n8n (and other future callers) exchange a username/password for a
    # token once, then send it as `Authorization: Token <key>` on every
    # call to /api/jobs/.
    path("api-token-auth/", obtain_auth_token, name="api-token-auth"),
]
