from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from src.modules.menu_scan.translation_provider import (
    TranslationProviderError,
    TranslationTimeoutError,
    TranslationUnavailableError,
)


@dataclass(frozen=True, slots=True)
class GeminiTranslationProvider:
    api_key: str
    api_base_url: str
    model: str
    timeout_seconds: float
    client: httpx.Client | None = None

    def translate_batch(
        self,
        *,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str | None]:
        if not texts:
            return []

        body = self._generate(
            texts=texts,
            source_language=source_language,
            target_language=target_language,
        )
        payload = _extract_json_payload(body)
        
        if not isinstance(payload, list):
            raise TranslationProviderError("gemini translation returned a non-array payload")

        # Pad with None if the result is shorter than the input
        result: list[str | None] = []
        for i in range(len(texts)):
            if i < len(payload) and isinstance(payload[i], str):
                result.append(payload[i])
            else:
                result.append(None)
                
        return result

    def _generate(
        self,
        *,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> dict[str, Any]:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            response = client.post(
                f"{self.api_base_url}/{_model_path(self.model)}:generateContent",
                params={"key": self.api_key},
                json=_build_request(
                    texts=texts,
                    source_language=source_language,
                    target_language=target_language,
                ),
            )
        except httpx.TimeoutException as error:
            raise TranslationTimeoutError("gemini translation timed out") from error
        except httpx.HTTPError as error:
            raise TranslationUnavailableError("gemini translation request failed") from error
        finally:
            if owns_client:
                client.close()

        if response.status_code in {408, 504}:
            raise TranslationTimeoutError("gemini translation timed out")
        if response.status_code == 429 or response.status_code >= 500:
            raise TranslationUnavailableError("gemini translation unavailable")
        if response.status_code >= 400:
            raise TranslationProviderError("gemini translation rejected the request")

        try:
            return response.json()
        except ValueError as error:
            raise TranslationProviderError("gemini translation returned invalid json") from error


def _model_path(model: str) -> str:
    normalized = model.strip("/")
    if normalized.startswith("models/"):
        return normalized
    return f"models/{normalized}"


def _build_request(
    *,
    texts: list[str],
    source_language: str,
    target_language: str,
) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": _build_prompt(
                            texts=texts,
                            source_language=source_language,
                            target_language=target_language,
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
        },
    }


def _build_prompt(
    *,
    texts: list[str],
    source_language: str,
    target_language: str,
) -> str:
    return (
        f"You are a translator. Translate the following array of strings from {source_language} to {target_language}.\n"
        "Rules:\n"
        "- Return a JSON array of strings with the exact same length as the input.\n"
        "- Keep the exact same order.\n"
        "- Translate each string contextually for a restaurant menu.\n"
        "- If a string cannot be translated, keep it unchanged or return null for that item.\n\n"
        f"Input texts:\n{json.dumps(texts, ensure_ascii=False)}"
    )


def _extract_json_payload(body: dict[str, Any]) -> Any:
    candidates = body.get("candidates") or []
    if not candidates:
        raise TranslationProviderError("gemini translation returned no candidates")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise TranslationProviderError("gemini translation returned empty content")

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise TranslationProviderError("gemini translation returned invalid json content") from error
