from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook


@dataclass(frozen=True)
class ExcelSource:
    workbook: Workbook
    source_file: str
    source_hash: str


def _read_bytes(source: str | Path | bytes | BinaryIO) -> tuple[bytes, str]:
    if isinstance(source, bytes):
        return source, "uploaded.xlsx"
    if isinstance(source, (str, Path)):
        path = Path(source)
        return path.read_bytes(), path.name
    payload = source.read()
    if hasattr(source, "seek"):
        source.seek(0)
    name = Path(getattr(source, "name", "uploaded.xlsx")).name
    return payload, name


def load_excel(source: str | Path | bytes | BinaryIO) -> ExcelSource:
    """Load stored cell values only; the project deliberately does not evaluate formulas."""
    payload, source_name = _read_bytes(source)
    workbook = load_workbook(BytesIO(payload), data_only=True, read_only=False)
    return ExcelSource(
        workbook=workbook,
        source_file=source_name,
        source_hash=sha256(payload).hexdigest(),
    )

