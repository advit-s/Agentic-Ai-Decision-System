from decision_system.llm.fake_provider import FakeProvider
from decision_system.llm.provider import LLMProvider


def default_provider() -> LLMProvider:
    return FakeProvider()
