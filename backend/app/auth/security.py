"""Fixed-credential auth for the MigrationProof dashboard.

No user accounts/OAuth for the MVP -- a single username/password (from
config/Secret Manager) grants a signed, time-limited session token used as a
Bearer token on all subsequent requests.
"""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

SESSION_MAX_AGE_SECONDS = 12 * 60 * 60  # 12 hours


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    secret = settings.dashboard_password or "insecure-dev-secret-change-me"
    return URLSafeTimedSerializer(secret_key=secret, salt="migrationproof-session")


def verify_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return username == settings.dashboard_username and password == settings.dashboard_password


def issue_session_token(username: str) -> str:
    return _serializer().dumps({"username": username})


def verify_session_token(token: str) -> bool:
    try:
        _serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
        return True
    except (BadSignature, SignatureExpired):
        return False
