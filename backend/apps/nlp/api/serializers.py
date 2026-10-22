"""
Serializers for NLP endpoints.
Conforms to Section 43 error contract and Section 14-16.
"""

from rest_framework import serializers


class NLPAnalyzeRequestSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=5000,
        trim_whitespace=False,
    )


class NLPTransliterateRequestSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=5000,
    )
    source_lang = serializers.CharField(
        default="hi",
        max_length=16,
    )
    target_script = serializers.CharField(
        default="Deva",
        max_length=16,
    )
