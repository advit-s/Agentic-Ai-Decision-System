"""Ollama provider placeholder for a future local-LLM milestone."""


class OllamaProvider:
    """v0.1 stub that prevents accidental local model execution."""

    def __init__(self, *args, **kwargs):
        # Keeping this as a stub avoids implying local LLM quality, latency, or
        # tool-calling behavior has been validated in v0.1.
        raise NotImplementedError("OllamaProvider is a v0.1 stub; use FakeProvider for now.")
