
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from clerk_backend_api import (
    AuthenticateRequestOptions,
    authenticate_request,
)
from clerk_backend_api.security.types import TokenVerificationErrorReason

# Load C:\ytBOT\backend\.env regardless of the working directory.
BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(BACKEND_ENV, override=True)

logger = logging.getLogger(__name__)

# Enables the Bearer authentication scheme in Swagger UI.
# Clerk will still perform the actual token verification.
bearer_scheme = HTTPBearer(auto_error=False)


def _sanitize_bearer_token(raw_token: str | None) -> str | None:
    """
    Sanitize token strings passed from Swagger UI, headers, or clients.
    Strips whitespace, newlines, surrounding quotes, and redundant 'Bearer ' prefixes.
    """
    if not raw_token:
        return None

    token = raw_token.strip()

    # Strip surrounding quotes from copy-pasting JSON or console logs
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        token = token[1:-1].strip()

    # Strip redundant Bearer prefixes (e.g. if typed into Swagger UI Authorize box)
    while token.lower().startswith("bearer "):
        token = token[7:].strip()

    # Strip quotes again in case they were inside "Bearer <token>"
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        token = token[1:-1].strip()

    return token or None


class _SanitizedRequest:
    """Lightweight Requestish protocol wrapper for clerk_backend_api."""

    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """
    Verify the Clerk session token and return the authenticated
    Clerk user ID from the token's 'sub' claim.
    """

    # Extract raw token from FastAPI's HTTPBearer credentials or from the Authorization header directly
    raw_token = credentials.credentials if credentials else None
    if not raw_token:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header:
            raw_token = auth_header

    token = _sanitize_bearer_token(raw_token)

    # Reject requests without a Bearer token.
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    secret_key = os.getenv("CLERK_SECRET_KEY")
    raw_jwt_key = os.getenv("CLERK_JWT_KEY")

    raw_parties = os.getenv(
        "CLERK_AUTHORIZED_PARTIES",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    authorized_parties = [
        item.strip()
        for item in raw_parties.split(",")
        if item.strip()
    ]

    if not secret_key:
        logger.error("CLERK_SECRET_KEY is not configured.")
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured.",
        )

    # Sanitize and validate the optional JWT public key.
    jwt_key = None

    if raw_jwt_key:
        cleaned_jwt_key = raw_jwt_key.replace("\\n", "\n").strip()

        if (
            "-----BEGIN PUBLIC KEY-----" in cleaned_jwt_key
            and "-----END PUBLIC KEY-----" in cleaned_jwt_key
        ):
            jwt_key = cleaned_jwt_key
        else:
            logger.warning(
                "CLERK_JWT_KEY appears incomplete or malformed; "
                "ignoring it to fall back to remote JWKS via secret key."
            )

    # Wrap request with sanitized Authorization header for Clerk SDK
    sanitized_request = _SanitizedRequest({"Authorization": f"Bearer {token}"})

    try:
        # Primary verification: Fast networkless verification using local jwt_key
        options = AuthenticateRequestOptions(
            secret_key=secret_key,
            jwt_key=jwt_key,
            authorized_parties=None,
            accepts_token=["session_token"],
        )

        state = authenticate_request(sanitized_request, options)

        # Fallback verification: If local jwt_key verification was rejected (e.g. key rotation),
        # retry with remote JWKS verification using the secret key.
        if not state.is_signed_in and jwt_key and secret_key:
            fallback_options = AuthenticateRequestOptions(
                secret_key=secret_key,
                jwt_key=None,
                authorized_parties=None,
                accepts_token=["session_token"],
            )
            fallback_state = authenticate_request(sanitized_request, fallback_options)
            if fallback_state.is_signed_in:
                state = fallback_state

        if not state.is_signed_in or not state.payload:
            reason = getattr(state, "reason", None)
            logger.warning(
                "Clerk authentication rejected: status=%s, reason=%s, "
                "message=%s, using_jwt_key=%s",
                getattr(state, "status", "unknown"),
                reason,
                getattr(state, "message", "unknown"),
                bool(jwt_key),
            )

            # Return specific, actionable error messages
            if reason == TokenVerificationErrorReason.TOKEN_EXPIRED:
                detail = "Token has expired and is no longer valid."
            elif reason == TokenVerificationErrorReason.TOKEN_INVALID_AUTHORIZED_PARTIES:
                detail = "Authorized party claim (azp) does not match any of the authorized parties."
            elif reason == TokenVerificationErrorReason.TOKEN_INVALID:
                detail = "Token is invalid and could not be verified."
            else:
                detail = "Authentication required."

            raise HTTPException(
                status_code=401,
                detail=detail,
            )

        # If the token contains an authorized party claim (azp) and authorized parties are configured, validate it
        token_azp = state.payload.get("azp")
        if token_azp and authorized_parties and token_azp not in authorized_parties:
            logger.warning(
                "Clerk token azp claim '%s' not in authorized parties %s",
                token_azp,
                authorized_parties,
            )
            raise HTTPException(
                status_code=401,
                detail="Authorized party claim (azp) does not match any of the authorized parties.",
            )

        user_id = state.payload.get("sub")

        if not user_id:
            logger.warning(
                "Clerk token is signed in but has no subject claim."
            )

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token.",
            )

        return user_id

    except HTTPException:
        raise

    except Exception as exc:
        # Never log the actual authentication token or secret.
        logger.warning(
            "Clerk token verification error: %s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        ) from exc

