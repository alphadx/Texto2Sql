"""Authentication and authorization helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

_INSECURE_SECRET_VALUES = {
    "",
    "changeme",
    "change-me",
    "default",
    "secret",
    "insecure",
    "test",
    "123456",
}

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthSettings:
    required: bool
    jwt_secret: str
    jwt_algorithm: str
    jwt_audience: str | None
    jwt_issuer: str | None


@dataclass(frozen=True)
class AuthContext:
    subject: str
    scopes: set[str]
    roles: set[str]
    claims: dict[str, Any]


def _normalize_to_set(raw: Any) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {value for value in raw.split() if value}
    if isinstance(raw, Iterable):
        return {str(value) for value in raw if str(value)}
    return {str(raw)}


def load_auth_settings_from_env() -> AuthSettings:
    required = os.getenv("AUTH_REQUIRED", "true").strip().lower() not in {"0", "false", "no"}
    secret = os.getenv("AUTH_JWT_SECRET", "")
    algorithm = os.getenv("AUTH_JWT_ALGORITHM", "HS256")
    audience = os.getenv("AUTH_JWT_AUDIENCE") or None
    issuer = os.getenv("AUTH_JWT_ISSUER") or None
    return AuthSettings(
        required=required,
        jwt_secret=secret,
        jwt_algorithm=algorithm,
        jwt_audience=audience,
        jwt_issuer=issuer,
    )


def validate_security_settings(settings: AuthSettings) -> None:
    if not settings.required:
        return

    secret = settings.jwt_secret.strip()
    if not secret:
        raise RuntimeError("AUTH_JWT_SECRET is required when AUTH_REQUIRED=true")
    if secret.lower() in _INSECURE_SECRET_VALUES:
        raise RuntimeError("AUTH_JWT_SECRET has an insecure value; set a strong random secret")
    if len(secret) < 32:
        raise RuntimeError("AUTH_JWT_SECRET must be at least 32 characters long")


def decode_access_token(token: str, settings: AuthSettings) -> AuthContext:
    options = {"verify_aud": settings.jwt_audience is not None}
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options=options,
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    scopes = _normalize_to_set(claims.get("scope") or claims.get("scopes"))
    roles = _normalize_to_set(claims.get("roles") or claims.get("role"))
    return AuthContext(subject=str(subject), scopes=scopes, roles=roles, claims=claims)


async def auth_context_dependency(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext | None:
    settings: AuthSettings = request.app.state.auth_settings
    if not settings.required:
        return None

    if getattr(request.state, "auth_context", None) is not None:
        return request.state.auth_context

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    return decode_access_token(credentials.credentials, settings)


def require_scopes(*required_scopes: str):
    required = set(required_scopes)

    async def _require(context: AuthContext | None = Depends(auth_context_dependency)) -> AuthContext | None:
        if context is None:
            return None
        missing = required.difference(context.scopes)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(sorted(missing))}",
            )
        return context

    return _require


def require_admin_access(*, admin_scopes: set[str], admin_roles: set[str]):
    async def _require(context: AuthContext | None = Depends(auth_context_dependency)) -> AuthContext | None:
        if context is None:
            return None
        has_scope_access = admin_scopes.issubset(context.scopes)
        has_role_access = bool(context.roles.intersection(admin_roles))
        if not has_scope_access and not has_role_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Administrative access required: include required scope(s) "
                    f"{', '.join(sorted(admin_scopes))} or role(s) {', '.join(sorted(admin_roles))}"
                ),
            )
        return context

    return _require
