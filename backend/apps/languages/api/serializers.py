"""
Serializers for Language resources.
"""

from rest_framework import serializers

from apps.languages.models import Language


class LanguageSerializer(serializers.ModelSerializer):
    """
    Public representation of a supported language and its capabilities.
    """

    class Meta:
        model = Language
        fields = [
            "code",
            "name",
            "native_name",
            "script_code",
            "is_rtl",
            "is_active",
            "translation_enabled",
            "detection_enabled",
            "transliteration_enabled",
            "sort_order",
        ]
        read_only_fields = fields
