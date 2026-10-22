"""
Common app URL configuration.
"""

from django.urls import path

from apps.common.api.health_views import HealthCheckView, PingView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path("ping/", PingView.as_view(), name="ping"),
]
