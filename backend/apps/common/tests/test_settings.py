"""
Tests for configuration settings integrity across environments.
"""

from django.conf import settings


def test_base_settings_loaded():
    assert settings.ROOT_URLCONF == "config.urls"
    assert "apps.common" in settings.INSTALLED_APPS
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "channels" in settings.INSTALLED_APPS
    assert hasattr(settings, "CELERY_BROKER_URL")


def test_rest_framework_exception_handler_registered():
    rf_settings = settings.REST_FRAMEWORK
    assert (
        rf_settings["EXCEPTION_HANDLER"]
        == "apps.common.api.exception_handler.custom_exception_handler"
    )
