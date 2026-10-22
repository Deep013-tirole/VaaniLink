"""
Views for Language registry.
"""

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.languages.api.serializers import LanguageSerializer
from apps.languages.models import Language


class LanguageListView(APIView):
    """
    List supported languages.
    Accepts query parameters:
      - active_only: boolean ('true' default)
      - q: search term filtering code, name, or native_name
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        active_only = request.query_params.get("active_only", "true").lower() in ("true", "1")
        search_query = request.query_params.get("q", "").strip()

        queryset = Language.objects.all()

        if active_only:
            queryset = queryset.filter(is_active=True)

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(native_name__icontains=search_query)
                | Q(code__iexact=search_query)
            )

        serializer = LanguageSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
