from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

import pandas as pd


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if result is pd.NA:
        return False
    try:
        return bool(result)
    except (TypeError, ValueError):
        return False


def decimal_text(value: Any) -> str | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean không phải numeric value hợp lệ.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NaN/Infinity không được phép trong canonical numeric value.")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Không thể chuẩn hóa numeric value: {value!r}") from exc
    if not decimal.is_finite():
        raise ValueError("NaN/Infinity không được phép trong canonical numeric value.")
    if decimal == 0:
        return "0"
    normalized = decimal.normalize()
    rendered = format(normalized, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def raw_value(value: Any) -> tuple[str | None, str]:
    if _is_missing(value):
        return None, "null"
    if isinstance(value, bool):
        return ("true" if value else "false"), "boolean"
    if isinstance(value, (datetime, pd.Timestamp)):
        timestamp = pd.Timestamp(value)
        return timestamp.isoformat(), "datetime"
    if isinstance(value, date):
        return value.isoformat(), "date"
    if isinstance(value, int):
        return str(value), "integer"
    if isinstance(value, (float, Decimal)):
        return decimal_text(value), "number"
    return unicodedata.normalize("NFC", str(value)), "text"


def canonicalize(value: Any) -> Any:
    if is_dataclass(value):
        return canonicalize(asdict(value))
    if _is_missing(value):
        return None
    if isinstance(value, dict):
        return {str(key): canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, set):
        return sorted((canonicalize(item) for item in value), key=lambda item: str(item))
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, (float, Decimal)):
        return decimal_text(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        normalized = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return canonicalize(value.item())
        except (TypeError, ValueError):
            pass
    return unicodedata.normalize("NFC", str(value))


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def content_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
