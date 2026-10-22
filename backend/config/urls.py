"""
Root URL Configuration for VaaniLink.
Exposes versioned API routes under `/api/v1/`.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Common / System Endpoints (Health check, ping)
    path("api/v1/", include("apps.common.urls")),
    # Phase 2 Endpoints
    path("api/v1/auth/", include("apps.accounts.urls.auth")),
    path("api/v1/users/", include("apps.accounts.urls.users")),
    path("api/v1/languages/", include("apps.languages.urls")),
    # Phase 3 Endpoints
    path("api/v1/conversations/", include("apps.conversations.urls")),
    path("api/v1/messages/", include("apps.messaging.urls")),
    # Phase 4 Endpoints
    path("api/v1/presence/", include("apps.realtime.urls")),
    # Phase 5 Endpoints
    path("api/v1/nlp/", include("apps.nlp.urls")),
    # Phase 6 Endpoints
    path("api/v1/translations/", include("apps.translation.urls")),
    # Phase 8 Privacy & Blocking Endpoints
    path("api/v1/privacy/", include("apps.privacy.urls")),
    path("api/v1/blocks/", include("apps.privacy.urls_blocks")),
]
