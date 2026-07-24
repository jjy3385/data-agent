"""검색된 Business Metadata를 LLM에 전달할 제한된 Metadata Context로 변환한다."""

from __future__ import annotations

from pydantic import BaseModel

from app.services.metadata_service import MetadataEntry

_KIND_TO_FIELD = {
    "entity": "entities",
    "dimension": "dimensions",
    "metric": "metrics",
    "filter": "filters",
    "grain": "grains",
    "join": "joins",
}


class MetadataContext(BaseModel):
    entities: dict[str, MetadataEntry]
    dimensions: dict[str, MetadataEntry]
    metrics: dict[str, MetadataEntry]
    filters: dict[str, MetadataEntry]
    grains: dict[str, MetadataEntry]
    joins: dict[str, MetadataEntry]

    def known_ids(self) -> set[str]:
        ids: set[str] = set()
        for group in (
            self.entities,
            self.dimensions,
            self.metrics,
            self.filters,
            self.grains,
            self.joins,
        ):
            ids.update(group.keys())
        return ids

    def as_prompt_dict(self) -> dict[str, list[dict[str, str]]]:
        """LLM Prompt에 넣을 수 있는 id/description(+sql_hint) 요약 구조를 만든다."""
        result: dict[str, list[dict[str, str]]] = {}
        for field_name in _KIND_TO_FIELD.values():
            group: dict[str, MetadataEntry] = getattr(self, field_name)
            result[field_name] = [
                {"id": entry.id, "description": entry.description, "sql_hint": entry.sql_hint}
                for entry in group.values()
            ]
        return result


def build(entries: list[MetadataEntry]) -> MetadataContext:
    groups: dict[str, dict[str, MetadataEntry]] = {field: {} for field in _KIND_TO_FIELD.values()}
    for entry in entries:
        field_name = _KIND_TO_FIELD[entry.kind]
        groups[field_name][entry.id] = entry
    return MetadataContext(**groups)
