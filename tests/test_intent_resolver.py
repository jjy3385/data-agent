import pytest

from app.services.intent_resolver import IntentContractViolationError, generate_runtime_intent
from app.services.llm_client import LLMUnavailableError
from tests.conftest import FakeLLMClient

pytestmark = pytest.mark.anyio


_VALID_INTENT = {
    "request_type": "lookup",
    "subject": "product",
    "requested_concepts": ["inventory", "safety_stock"],
    "requested_output": "list",
    "explicit_parameters": {},
    "requires_clarification": False,
    "clarification_reason": None,
}

_VALID_CLARIFICATION_INTENT = {
    "request_type": "lookup",
    "subject": "",
    "requested_concepts": [],
    "requested_output": "list",
    "explicit_parameters": {},
    "requires_clarification": True,
    "clarification_reason": "어떤 제품인지 명확하지 않습니다.",
}


async def test_generate_runtime_intent_success():
    fake = FakeLLMClient(json_responses=[_VALID_INTENT])
    intent = await generate_runtime_intent("현재 재고가 안전재고보다 부족한 제품을 보여줘", fake)
    assert intent.request_type == "lookup"
    assert intent.subject == "product"
    assert intent.requires_clarification is False
    assert fake.json_calls[0][2] == 2000  # max_completion_tokens


async def test_generate_runtime_intent_valid_clarification():
    fake = FakeLLMClient(json_responses=[_VALID_CLARIFICATION_INTENT])
    intent = await generate_runtime_intent("아무거나", fake)
    assert intent.requires_clarification is True
    assert intent.clarification_reason


async def test_llm_unavailable_propagates():
    fake = FakeLLMClient(fail_with=LLMUnavailableError("no provider"))
    with pytest.raises(LLMUnavailableError):
        await generate_runtime_intent("질문", fake)


@pytest.mark.parametrize(
    "broken",
    [
        {**_VALID_INTENT, "request_type": "not_a_real_type"},
        {**_VALID_INTENT, "requested_output": "not_a_real_output"},
        {**_VALID_INTENT, "extra_field": "not allowed"},
        {**_VALID_INTENT, "requested_concepts": []},
        {**_VALID_INTENT, "requires_clarification": True, "clarification_reason": None},
        {**_VALID_INTENT, "clarification_reason": "should be null when false"},
        {k: v for k, v in _VALID_INTENT.items() if k != "subject"},
    ],
)
async def test_contract_violations_are_rejected(broken):
    fake = FakeLLMClient(json_responses=[broken])
    with pytest.raises(IntentContractViolationError):
        await generate_runtime_intent("질문", fake)


async def test_explicit_parameters_reject_nested_object():
    broken = {**_VALID_INTENT, "explicit_parameters": {"period": {"nested": "not allowed"}}}
    fake = FakeLLMClient(json_responses=[broken])
    with pytest.raises(IntentContractViolationError):
        await generate_runtime_intent("질문", fake)
