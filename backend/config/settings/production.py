"""
Production settings for VaaniLink.
Hardened for security, performance, and reliability.
"""

import os

from .base import *

DEBUG = False

# Ensure SECRET_KEY is set in environment
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# PostgreSQL is strictly required in production
if not os.getenv("DATABASE_URL"):
    raise ValueError("DATABASE_URL environment variable must be set in production.")

# HTTPS / SSL Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
