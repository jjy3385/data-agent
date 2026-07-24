import pytest

from app.services.intent_resolver import RuntimeIntent
from app.services.metadata_retriever import MetadataNotFoundError, retrieve


def _intent(subject: str, concepts: list[str]) -> RuntimeIntent:
    return RuntimeIntent(
        request_type="lookup",
        subject=subject,
        requested_concepts=concepts,
        requested_output="list",
        explicit_parameters={},
        requires_clarification=False,
        clarification_reason=None,
    )


def test_retrieve_succeeds_for_representative_question():
    intent = _intent("product", ["inventory", "safety_stock"])
    entries = retrieve(intent)
    assert len(entries) == 8


def test_retrieve_succeeds_with_korean_aliases():
    intent = _intent("제품", ["재고", "안전재고"])
    entries = retrieve(intent)
    assert len(entries) == 8


def test_retrieve_normalizes_case_and_whitespace():
    intent = _intent("  Product  ", [" Inventory ", "SAFETY_STOCK"])
    entries = retrieve(intent)
    assert len(entries) == 8


def test_retrieve_rejects_unknown_subject():
    intent = _intent("supplier", ["inventory", "safety_stock"])
    with pytest.raises(MetadataNotFoundError):
        retrieve(intent)


def test_retrieve_rejects_when_only_one_concept_matches():
    intent = _intent("product", ["inventory"])
    with pytest.raises(MetadataNotFoundError):
        retrieve(intent)


def test_retrieve_rejects_out_of_scope_concepts():
    intent = _intent("product", ["sales", "purchasing"])
    with pytest.raises(MetadataNotFoundError):
        retrieve(intent)
