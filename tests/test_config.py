from decision_system.config import load_settings


def test_nvidia_nim_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_NIM_BASE_URL", "https://test.nvidia.com/v1")
    monkeypatch.setenv("NVIDIA_NIM_MODEL", "nvidia/test-model")
    monkeypatch.setenv("NVIDIA_TEMPERATURE", "0")
    monkeypatch.setenv("NVIDIA_TOP_P", "0.9")
    monkeypatch.setenv("NVIDIA_MAX_TOKENS", "2048")
    monkeypatch.setenv("NVIDIA_REASONING_ENABLED", "true")
    monkeypatch.setenv("NVIDIA_REASONING_EFFORT", "medium")

    settings = load_settings()

    assert settings.nvidia_api_key == "test-key"
    assert settings.nvidia_nim_base_url == "https://test.nvidia.com/v1"
    assert settings.nvidia_nim_model == "nvidia/test-model"
    assert settings.nvidia_temperature == 0
    assert settings.nvidia_top_p == 0.9
    assert settings.nvidia_max_tokens == 2048
    assert settings.nvidia_reasoning_enabled is True
    assert settings.nvidia_reasoning_effort == "medium"


def test_nvidia_nim_defaults_load(monkeypatch):
    monkeypatch.delenv("NVIDIA_NIM_BASE_URL", raising=False)

    settings = load_settings()

    assert settings.nvidia_nim_base_url == "https://integrate.api.nvidia.com/v1"
