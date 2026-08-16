import pytest
from pydantic import ValidationError
from app.features.providers.contracts import ProviderConfig, ProviderKind, validate_provider_url, ProviderConfigError

def test_only_approved_provider_targets_are_allowed():
    assert validate_provider_url("http://127.0.0.1:11434/api/chat", ProviderKind.OLLAMA).hostname == "127.0.0.1"
    assert validate_provider_url("https://api.openai.com/v1", ProviderKind.OPENAI).scheme == "https"
    assert validate_provider_url("https://openrouter.ai/api/v1", ProviderKind.OPENROUTER).hostname == "openrouter.ai"

@pytest.mark.parametrize("url", ["http://169.254.169.254/latest", "http://192.168.1.2:80", "https://evil.example/v1", "http://127.0.0.1:11434@evil.example/"])
def test_ssrf_and_allowlist_rejections(url):
    with pytest.raises((ProviderConfigError, ValidationError)): validate_provider_url(url, ProviderKind.OPENAI)

def test_external_config_has_bounded_timeout_and_never_accepts_secret():
    config=ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="any", timeout_seconds=20)
    assert config.secret_env == "OPENAI_API_KEY" and config.timeout_seconds == 20
    with pytest.raises(ValueError): ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="x", timeout_seconds=0)


def test_local_openai_accepts_loopback_only():
    config=ProviderConfig(kind=ProviderKind.LOCAL_OPENAI, base_url="http://localhost:8000/v1", model="local", timeout_seconds=5)
    assert config.secret_env == ""


def test_secret_environment_name_is_provider_controlled():
    with pytest.raises((ProviderConfigError, ValidationError)): ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="x", timeout_seconds=2, secret_env="EVIL")


def test_provider_config_is_immutable_after_validation():
    cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2)
    with pytest.raises(Exception): cfg.base_url="http://169.254.169.254"


def test_openrouter_metadata_fields_are_bounded():
    cfg=ProviderConfig(kind=ProviderKind.OPENROUTER,base_url="https://openrouter.ai/api/v1",model="x",timeout_seconds=2,referer="https://localhost",title="HarnessForge")
    assert cfg.referer=="https://localhost" and cfg.title=="HarnessForge"
    with pytest.raises(Exception): ProviderConfig(kind=ProviderKind.OPENROUTER,base_url="https://openrouter.ai/api/v1",model="x",timeout_seconds=2,referer="http://evil")


def test_provider_copy_cannot_route_wrong_secret_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","openai-secret"); monkeypatch.setenv("OPENROUTER_API_KEY","router-secret")
    original=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2)
    copied=original.model_copy(update={"kind":ProviderKind.OPENROUTER,"base_url":"https://openrouter.ai/api/v1"})
    assert copied.secret_env=="OPENROUTER_API_KEY"


def test_external_provider_endpoint_path_and_port_are_fixed():
    with pytest.raises(ProviderConfigError): validate_provider_url("https://api.openai.com:8443/v1", ProviderKind.OPENAI)
    with pytest.raises(ProviderConfigError): validate_provider_url("https://api.openai.com/v1/other", ProviderKind.OPENAI)
    with pytest.raises(ProviderConfigError): validate_provider_url("https://openrouter.ai/api/v1/other", ProviderKind.OPENROUTER)
