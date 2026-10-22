"""
Development settings for VaaniLink.
Optimized for local developer experience and debugging.
"""

from .base import *

DEBUG = True

# In development, allow broader host access if needed
ALLOWED_HOSTS = ["*"]

# Enable browsable API renderer in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Development channel layer fallback to in-memory if Redis is offline
if os.getenv("USE_INMEMORY_CHANNELS", "false").lower() in ("true", "1", "yes"):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

# Email backend: print to console in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
