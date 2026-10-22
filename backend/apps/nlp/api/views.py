"""
Views for NLP Analysis and Transliteration endpoints.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.nlp.api.serializers import (
    NLPAnalyzeRequestSerializer,
    NLPTransliterateRequestSerializer,
)
from apps.nlp.pipeline import NLPPipeline
from apps.nlp.transliteration import TransliterationService


class NLPAnalyzeView(APIView):
    """
    Analyze text with the full NLP Language Intelligence Pipeline.
    POST /api/v1/nlp/analyze/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = NLPAnalyzeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        result = NLPPipeline.process(text)

        return Response(result.to_dict(), status=status.HTTP_200_OK)


class NLPTransliterateView(APIView):
    """
    Transliterate romanized text to target script.
    POST /api/v1/nlp/transliterate/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = NLPTransliterateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        source_lang = serializer.validated_data["source_lang"]
        target_script = serializer.validated_data["target_script"]

        transliterated = TransliterationService.transliterate(
            text, source_lang=source_lang, target_script=target_script
        )

        return Response(
            {
                "original_text": text,
                "source_lang": source_lang,
                "target_script": target_script,
                "transliterated_text": transliterated,
            },
            status=status.HTTP_200_OK,
        )
