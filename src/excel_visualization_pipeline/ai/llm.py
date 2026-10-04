from __future__ import annotations

from dataclasses import dataclass
import json
import socket
import time
from typing import Any, Protocol
from urllib import error, request


@dataclass(frozen=True)
class LLMResult:
    content: str
    model: str
    provider_request_id: str | None = None
    latency_ms: int | None = None
    attempt_count: int = 1


class ProviderError(RuntimeError):
    def __init__(
        self, code: str, message: str, *, retryable: bool = False,
        latency_ms: int | None = None, attempt_count: int = 1,
    ):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.latency_ms = latency_ms
        self.attempt_count = attempt_count


class LLMAdapter(Protocol):
    provider_name: str
    model: str

    def generate(self, *, system_prompt: str, payload: dict[str, Any]) -> LLMResult: ...

    def check_model(self) -> dict[str, Any]: ...


class DisabledLLMAdapter:
    provider_name = "disabled"

    def __init__(self, model: str, reason: str):
        self.model = model
        self.reason = reason

    def generate(self, *, system_prompt: str, payload: dict[str, Any]) -> LLMResult:
        del system_prompt, payload
        raise ProviderError(self.reason, "Dịch vụ trí tuệ nhân tạo bên ngoài chưa được phép sử dụng.")

    def check_model(self) -> dict[str, Any]:
        return {"available": False, "code": self.reason, "model": self.model}


class NineRouterLLMAdapter:
    provider_name = "9router"

    def __init__(
        self, *, api_key: str, base_url: str, model: str,
        timeout_seconds: float = 12, max_retries: int = 0,
        max_output_tokens: int = 700,
        report_max_output_tokens: int = 2400,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = min(2, max(0, max_retries))
        self.max_output_tokens = min(1200, max(300, max_output_tokens))
        self.report_max_output_tokens = min(3000, max(700, report_max_output_tokens))

    def _request_json(self, path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, str]]:
        started_at = time.monotonic()
        encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8") if body is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            req = request.Request(f"{self.base_url}{path}", data=encoded, headers=headers, method=method)
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    parsed = json.loads(response.read().decode("utf-8"))
                    headers = dict(response.headers.items())
                    headers["x-evp-latency-ms"] = str(round((time.monotonic() - started_at) * 1000))
                    headers["x-evp-attempt-count"] = str(attempt + 1)
                    return parsed, headers
            except error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                code = "rate_limited" if exc.code == 429 else "unauthorized" if exc.code in {401, 403} else "provider_http_error"
                if retryable and attempt + 1 < attempts:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                raise ProviderError(code, f"9Router trả HTTP {exc.code}.", retryable=retryable) from exc
            except (error.URLError, socket.timeout, TimeoutError) as exc:
                if attempt + 1 < attempts:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                raise ProviderError("timeout", "Không nhận được phản hồi từ 9Router trong thời gian cho phép.", retryable=True) from exc
            except (json.JSONDecodeError, UnicodeError, TypeError) as exc:
                raise ProviderError("malformed_provider_response", "9Router trả về nội dung không đọc được.") from exc
        raise ProviderError("provider_unavailable", "9Router không khả dụng.")

    def generate(self, *, system_prompt: str, payload: dict[str, Any]) -> LLMResult:
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.report_max_output_tokens if payload.get("schemaVersion") == "ai-insight-provider-input-v5" else self.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(
                    payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
                )},
            ],
        }
        parsed, headers = self._request_json("/chat/completions", method="POST", body=body)
        try:
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("malformed_provider_response", "Phản hồi của 9Router thiếu nội dung từ mô hình.") from exc
        if not isinstance(content, str):
            raise ProviderError("malformed_provider_response", "Nội dung từ mô hình không đúng định dạng yêu cầu.")
        return LLMResult(
            content,
            str(parsed.get("model") or self.model),
            headers.get("x-request-id"),
            int(headers.get("x-evp-latency-ms", "0")),
            int(headers.get("x-evp-attempt-count", "1")),
        )

    def check_model(self) -> dict[str, Any]:
        parsed, _ = self._request_json("/models")
        ids = {str(item.get("id")) for item in parsed.get("data", []) if isinstance(item, dict)}
        return {"available": self.model in ids, "model": self.model, "provider": self.provider_name}
