"""Outbound provider contracts and strict endpoint allowlist."""
from enum import StrEnum
from ipaddress import ip_address
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core.config import CAPS
class ProviderConfigError(ValueError): pass
class ProviderKind(StrEnum): OLLAMA="ollama"; LOCAL_OPENAI="local_openai"; OPENAI="openai"; OPENROUTER="openrouter"; MISTRAL="mistral"

def validate_provider_url(value: str, kind: ProviderKind):
    parsed=urlparse(value)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ProviderConfigError("invalid provider port") from exc
    if parsed.username or parsed.password or parsed.fragment or parsed.query or parsed.scheme not in {"http","https"} or not parsed.hostname: raise ProviderConfigError("invalid provider URL")
    host=parsed.hostname.casefold()
    is_loopback=False
    try: is_loopback=ip_address(host).is_loopback
    except ValueError: is_loopback=host=="localhost"
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ProviderConfigError("invalid provider port")
    if kind in {ProviderKind.OLLAMA,ProviderKind.LOCAL_OPENAI} and (not is_loopback or parsed.scheme != "http"):
        raise ProviderConfigError("local providers require HTTP loopback")
    if kind==ProviderKind.OPENAI:
        if host!="api.openai.com" or parsed.scheme!="https" or parsed.port not in {None,443} or parsed.path.rstrip("/")!="/v1":
            raise ProviderConfigError("OpenAI endpoint is fixed")
    if kind==ProviderKind.OPENROUTER:
        if host!="openrouter.ai" or parsed.scheme!="https" or parsed.port not in {None,443} or parsed.path.rstrip("/")!="/api/v1":
            raise ProviderConfigError("OpenRouter endpoint is fixed")
    if kind==ProviderKind.MISTRAL:
        if host!="api.mistral.ai" or parsed.scheme!="https" or parsed.port not in {None,443} or parsed.path.rstrip("/")!="/v1":
            raise ProviderConfigError("Mistral endpoint is fixed")
    if not is_loopback and parsed.scheme!="https": raise ProviderConfigError("external providers require TLS")
    return parsed
class ProviderConfig(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True, validate_assignment=True)
    kind: ProviderKind
    base_url: str
    model: str=Field(min_length=1,max_length=256)
    timeout_seconds: float=Field(gt=0,le=CAPS.max_run_seconds)
    secret_env: str=""
    referer: str | None = Field(default=None, max_length=512)
    title: str | None = Field(default=None, max_length=128)
    def model_copy(self, *, update=None, deep=False):
        data=self.model_dump(mode="python")
        if update: data.update(update)
        if data.get("kind") == ProviderKind.OPENAI: data["secret_env"]=""
        elif data.get("kind") == ProviderKind.OPENROUTER: data["secret_env"]=""
        elif data.get("kind") == ProviderKind.MISTRAL: data["secret_env"]=""
        else: data["secret_env"]=""
        return type(self).model_validate(data)

    @model_validator(mode="after")
    def validate_endpoint_and_secret_policy(self):
        validate_provider_url(self.base_url, self.kind)
        expected = "OPENAI_API_KEY" if self.kind == ProviderKind.OPENAI else "OPENROUTER_API_KEY" if self.kind == ProviderKind.OPENROUTER else "MISTRAL_API_KEY" if self.kind == ProviderKind.MISTRAL else ""
        if self.secret_env not in {"", expected}:
            raise ProviderConfigError("secret_env is provider-controlled")
        object.__setattr__(self, "secret_env", expected)
        if self.kind == ProviderKind.OPENROUTER and self.referer is not None and not self.referer.startswith("https://"): raise ProviderConfigError("OpenRouter referer must use TLS")
        if self.kind != ProviderKind.OPENROUTER and (self.referer is not None or self.title is not None): raise ProviderConfigError("provider metadata is only supported by OpenRouter")
        return self

# DataflowApproval is defined in adapters and re-exported lazily for compatibility.
