from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ParserConfig:
    header_search_rows: int = 20
    project_column: str = "Dự án"
    unit_column: str = "Đơn vị"
    result_header_patterns: tuple[str, ...] = ("kết quả triển khai",)
    hierarchy_rules: tuple[dict[str, Any], ...] = (
        {
            "name": "numbered_section",
            "pattern": r"^\s*\d+\.\d+[\.\s]",
            "entity_level": "section",
            "parent_strategy": "project",
            "strip_marker": False,
            "confidence": "high",
        },
        {
            "name": "plus_subitem",
            "pattern": r"^\s*\+\s*",
            "entity_level": "subitem",
            "parent_strategy": "previous_item_or_project",
            "strip_marker": True,
            "confidence": "high",
        },
        {
            "name": "dash_item",
            "pattern": r"^\s*-\s*",
            "entity_level": "item",
            "parent_strategy": "section_or_project",
            "strip_marker": True,
            "confidence": "high",
        },
    )
    fallback_entity_level: str = "item"
    fallback_parent_strategy: str = "project"
    blank_markers: tuple[str, ...] = ("", "\u00a0")
    missing_markers: tuple[str, ...] = ("-", "n/a", "na", "unknown")
    metric_aliases: dict[str, str] = field(default_factory=dict)
    unit_aliases: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path | None = None) -> "ParserConfig":
        if path is None:
            return cls()
        payload: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(
            header_search_rows=int(payload.get("header_search_rows", 20)),
            project_column=str(payload.get("project_column", "Dự án")),
            unit_column=str(payload.get("unit_column", "Đơn vị")),
            result_header_patterns=tuple(payload.get("result_header_patterns", ["kết quả triển khai"])),
            hierarchy_rules=tuple(payload.get("hierarchy_rules", cls.hierarchy_rules)),
            fallback_entity_level=str(payload.get("fallback_entity_level", "item")),
            fallback_parent_strategy=str(payload.get("fallback_parent_strategy", "project")),
            blank_markers=tuple(payload.get("blank_markers", ["", "\u00a0"])),
            missing_markers=tuple(payload.get("missing_markers", ["-", "n/a", "na", "unknown"])),
            metric_aliases={str(k).casefold(): str(v) for k, v in payload.get("metric_aliases", {}).items()},
            unit_aliases={str(k).casefold(): str(v) for k, v in payload.get("unit_aliases", {}).items()},
        )
