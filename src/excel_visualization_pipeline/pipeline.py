from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .config import ParserConfig
from .ingestion import load_excel
from .models import ValidationReport
from .parser import parse_workbook
from .validation import validate_dataset


@dataclass
class PipelineResult:
    data: pd.DataFrame
    entities: pd.DataFrame
    report: ValidationReport
    manifest: dict


def run_pipeline(
    source: str | Path | bytes | BinaryIO,
    config_path: str | Path | None = None,
) -> PipelineResult:
    config = ParserConfig.from_yaml(config_path) if config_path else ParserConfig()
    loaded = load_excel(source)
    parsed = parse_workbook(loaded, config)
    report = validate_dataset(parsed.data, parsed.issues, parsed.entities)
    return PipelineResult(data=parsed.data, entities=parsed.entities, report=report, manifest=parsed.manifest)


def export_result(result: PipelineResult, output_dir: str | Path) -> None:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    result.data.to_csv(destination / "normalized_data.csv", index=False, encoding="utf-8-sig")
    result.entities.to_csv(destination / "entities.csv", index=False, encoding="utf-8-sig")
    (destination / "manifest.json").write_text(
        json.dumps(result.manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    (destination / "validation_report.json").write_text(
        json.dumps(result.report.as_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
