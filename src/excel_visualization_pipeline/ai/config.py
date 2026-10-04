from __future__ import annotations

from dataclasses import dataclass
import os


def _flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    external_allowed: bool
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int = 700
    report_max_output_tokens: int = 2400

    @classmethod
    def from_env(cls) -> "AIConfig":
        raw_key = os.environ.get("GEMINI_API_KEY", "").strip()
        api_key = raw_key if raw_key and not raw_key.startswith("your_") else None
        return cls(
            enabled=_flag("EVP_AI_ENABLED"),
            external_allowed=_flag("EVP_AI_EXTERNAL_ALLOWED"),
            api_key=api_key,
            base_url=os.environ.get(
                "GEMINI_API_BASE_URL", "https://9router.cool.khokey.com/v1"
            ).rstrip("/"),
            model=os.environ.get("GEMINI_MODEL", "ag/gemini-3.7-flash-low"),
            timeout_seconds=max(1.0, float(os.environ.get("EVP_AI_TIMEOUT_SECONDS", "12"))),
            max_retries=min(2, max(0, int(os.environ.get("EVP_AI_MAX_RETRIES", "0")))),
            max_output_tokens=min(1200, max(300, int(os.environ.get("EVP_AI_MAX_OUTPUT_TOKENS", "700")))),
            report_max_output_tokens=min(3000, max(700, int(os.environ.get("EVP_AI_REPORT_MAX_OUTPUT_TOKENS", "2400")))),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    @property
    def can_call_external(self) -> bool:
        return self.enabled and self.external_allowed and self.configured
