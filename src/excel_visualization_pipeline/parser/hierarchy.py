from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from hashlib import sha1
from typing import Any

from ..config import ParserConfig


ENTITY_COLUMNS = [
    "sheet_name",
    "source_row",
    "project_id",
    "project_label",
    "entity_id",
    "parent_entity_id",
    "entity_level",
    "entity_depth",
    "entity_label",
    "entity_path",
    "unit_raw",
    "unit_original",
    "unit_normalized",
    "effective_unit",
    "unit_source_level",
    "unit_source_entity_id",
    "parser_rule",
    "parser_confidence",
]


def clean_label(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\u00a0", " ").split()).strip()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    ascii_text = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "entity"


@dataclass(frozen=True)
class EntityNode:
    sheet_name: str
    source_row: int
    project_id: str
    project_label: str
    entity_id: str
    parent_entity_id: str | None
    entity_level: str
    entity_depth: int
    entity_label: str
    entity_path: str
    unit_raw: str | None
    unit_original: str | None
    unit_normalized: str | None
    effective_unit: str | None
    unit_source_level: str | None
    unit_source_entity_id: str | None
    parser_rule: str
    parser_confidence: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EntityTreeBuilder:
    """Config-driven parent-child state machine for one worksheet."""

    def __init__(self, sheet_name: str, config: ParserConfig):
        self.sheet_name = sheet_name
        self.config = config
        self.nodes: list[EntityNode] = []
        self.by_id: dict[str, EntityNode] = {}
        self.current_project: EntityNode | None = None
        self.current_section: EntityNode | None = None
        self.previous_item: EntityNode | None = None
        self._path_occurrences: dict[str, int] = {}

    def _entity_id(self, path: str) -> str:
        occurrence = self._path_occurrences.get(path, 0) + 1
        self._path_occurrences[path] = occurrence
        digest = sha1(f"{self.sheet_name}|{path}|{occurrence}".encode("utf-8")).hexdigest()[:12]
        return f"{_slug(path.split(' > ')[-1])}-{digest}"

    def _normalize_unit(self, unit: str | None) -> str | None:
        if unit is None:
            return None
        return self.config.unit_aliases.get(unit.casefold(), unit)

    def _parent_for(self, strategy: str) -> EntityNode | None:
        if strategy == "project":
            return self.current_project
        if strategy == "section_or_project":
            return self.current_section or self.current_project
        if strategy == "previous_item_or_project":
            return self.previous_item or self.current_section or self.current_project
        raise ValueError(f"Unknown parent strategy: {strategy}")

    def _create_node(
        self,
        *,
        row: int,
        label: str,
        level: str,
        parent: EntityNode | None,
        unit_raw: str | None,
        rule: str,
        confidence: str,
    ) -> EntityNode:
        path = label if parent is None else f"{parent.entity_path} > {label}"
        entity_id = self._entity_id(path)
        if level == "project":
            project_id = entity_id
            project_label = label
        else:
            if self.current_project is None:
                raise ValueError("Child entity cannot be created without a project")
            project_id = self.current_project.project_id
            project_label = self.current_project.project_label

        if unit_raw:
            effective_unit = unit_raw
            unit_source_level = level
            unit_source_entity_id = entity_id
        elif parent:
            effective_unit = parent.effective_unit
            unit_source_level = parent.unit_source_level
            unit_source_entity_id = parent.unit_source_entity_id
        else:
            effective_unit = None
            unit_source_level = None
            unit_source_entity_id = None

        node = EntityNode(
            sheet_name=self.sheet_name,
            source_row=row,
            project_id=project_id,
            project_label=project_label,
            entity_id=entity_id,
            parent_entity_id=parent.entity_id if parent else None,
            entity_level=level,
            entity_depth=0 if parent is None else parent.entity_depth + 1,
            entity_label=label,
            entity_path=path,
            unit_raw=unit_raw,
            unit_original=unit_raw,
            unit_normalized=self._normalize_unit(effective_unit),
            effective_unit=effective_unit,
            unit_source_level=unit_source_level,
            unit_source_entity_id=unit_source_entity_id,
            parser_rule=rule,
            parser_confidence=confidence,
        )
        self.nodes.append(node)
        self.by_id[node.entity_id] = node
        return node

    def add_row(self, row: int, sequence: Any, raw_label: Any, raw_unit: Any) -> EntityNode | None:
        label = clean_label(raw_label)
        if not label:
            return None
        unit_raw = clean_label(raw_unit) or None

        if isinstance(sequence, (int, float)) and not isinstance(sequence, bool):
            node = self._create_node(
                row=row,
                label=label,
                level="project",
                parent=None,
                unit_raw=unit_raw,
                rule="project_sequence_number",
                confidence="high",
            )
            self.current_project = node
            self.current_section = None
            self.previous_item = None
            return node

        if self.current_project is None:
            return None

        matched_rule: dict[str, Any] | None = None
        for rule in self.config.hierarchy_rules:
            if re.search(str(rule["pattern"]), label):
                matched_rule = rule
                break

        if matched_rule:
            level = str(matched_rule["entity_level"])
            parent = self._parent_for(str(matched_rule["parent_strategy"]))
            normalized_label = (
                re.sub(str(matched_rule["pattern"]), "", label).strip()
                if matched_rule.get("strip_marker")
                else label
            )
            node = self._create_node(
                row=row,
                label=normalized_label,
                level=level,
                parent=parent,
                unit_raw=unit_raw,
                rule=str(matched_rule["name"]),
                confidence=str(matched_rule.get("confidence", "high")),
            )
        else:
            parent = self._parent_for(self.config.fallback_parent_strategy)
            node = self._create_node(
                row=row,
                label=label,
                level=self.config.fallback_entity_level,
                parent=parent,
                unit_raw=unit_raw,
                rule="fallback_entity",
                confidence="medium",
            )

        if node.entity_level == "section":
            self.current_section = node
            self.previous_item = None
        elif node.entity_level == "item":
            self.previous_item = node
        return node
