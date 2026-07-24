"""RuntimeIntent 기반 Business Metadata 검색과 고정 Demo Scope 판정.

RuntimeIntent가 이미 구조화한 subject/requested_concepts에만 Alias 매칭을 적용한다.
질문 원문 전체나 SQL을 직접 대상으로 하지 않는다(NFR-003).
"""

from __future__ import annotations

from app.services import metadata_service
from app.services.intent_resolver import RuntimeIntent
from app.services.metadata_service import MetadataEntry


class MetadataNotFoundError(RuntimeError):
    """질문에 필요한 Business Metadata가 없거나 고정 Demo Scope를 벗어날 때 발생한다."""


def _normalize(value: str) -> str:
    return value.strip().lower()


def retrieve(intent: RuntimeIntent) -> list[MetadataEntry]:
    """subject가 Entity Alias와 일치하고 requested_concepts가 inventory·safety_stock
    두 그룹에 각각 최소 1개 일치해야 성공한다. 그렇지 않으면 MetadataNotFoundError.
    """
    subject = _normalize(intent.subject)
    concepts = {_normalize(concept) for concept in intent.requested_concepts}

    if subject not in metadata_service.ENTITY_ALIASES:
        raise MetadataNotFoundError("질문의 대상이 고정 Demo Scope의 제품 Entity와 일치하지 않습니다.")

    if not (concepts & metadata_service.INVENTORY_CONCEPT_ALIASES):
        raise MetadataNotFoundError("재고 개념을 고정 Demo Scope에서 찾을 수 없습니다.")

    if not (concepts & metadata_service.SAFETY_STOCK_CONCEPT_ALIASES):
        raise MetadataNotFoundError("안전재고 개념을 고정 Demo Scope에서 찾을 수 없습니다.")

    return metadata_service.all_entries()
