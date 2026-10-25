"""Shared Gemini client helpers (API key stays on the backend only)."""

from __future__ import annotations

from google import genai

from app.config import get_settings


class GeminiConfigError(RuntimeError):
    """Raised when GEMINI_API_KEY is missing or empty."""


class GeminiAPIError(RuntimeError):
    """Raised when a Gemini API call fails or returns unusable data."""


def require_gemini_api_key() -> str:
    key = (get_settings().gemini_api_key or "").strip()
    if not key:
        raise GeminiConfigError(
            "GEMINI_API_KEY is not configured. Add it to apps/api/.env "
            "(backend only — never expose it to the frontend)."
        )
    return key


def get_gemini_client() -> genai.Client:
    return genai.Client(api_key=require_gemini_api_key())


def get_gemini_model() -> str:
    return get_settings().gemini_model


def raise_from_gemini_error(exc: Exception) -> None:
    """Normalize Gemini SDK errors into GeminiAPIError (never returns)."""
    from google.genai.errors import APIError, ClientError

    message = str(exc).lower()
    if isinstance(exc, ClientError) and (
        "429" in message or "resource_exhausted" in message or "rate" in message
    ):
        raise GeminiAPIError(
            "Gemini rate limit reached. Try again in a moment."
        ) from exc
    if isinstance(exc, ClientError) and (
        "401" in message
        or "403" in message
        or "api key" in message
        or "permission" in message
    ):
        raise GeminiAPIError(
            "Gemini authentication failed. Check GEMINI_API_KEY."
        ) from exc
    if isinstance(exc, (APIError, ClientError)):
        raise GeminiAPIError(f"Gemini API error: {exc}") from exc
    raise GeminiAPIError(f"Gemini request failed: {exc}") from exc
