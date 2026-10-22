"""
System health check and ping API views.
"""

from django.core.cache import cache
from django.db import connection
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class PingView(APIView):
    """
    Lightweight ping endpoint for load balancer heartbeat probes.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({"status": "ok", "service": "vaanilink-backend"}, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """
    Comprehensive health check testing database and cache connectivity.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        health_status = {
            "status": "healthy",
            "components": {
                "database": "unknown",
                "cache": "unknown",
            },
        }
        all_healthy = True

        # Check Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    health_status["components"]["database"] = "healthy"
                else:
                    health_status["components"]["database"] = "unhealthy"
                    all_healthy = False
        except Exception as exc:
            health_status["components"]["database"] = f"unhealthy: {str(exc)}"
            all_healthy = False

        # Check Cache
        try:
            cache_key = "health_check_probe"
            cache.set(cache_key, "ok", timeout=10)
            val = cache.get(cache_key)
            if val == "ok":
                health_status["components"]["cache"] = "healthy"
            else:
                health_status["components"]["cache"] = "unhealthy"
                all_healthy = False
        except Exception as exc:
            health_status["components"]["cache"] = f"unhealthy: {str(exc)}"
            all_healthy = False

        if not all_healthy:
            health_status["status"] = "degraded"
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_status, status=status.HTTP_200_OK)
