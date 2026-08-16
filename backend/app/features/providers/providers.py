"""Provider-specific adapter names and dispatch."""
from app.features.providers.adapters import OpenAICompatibleAdapter
from app.features.providers.contracts import ProviderConfig, ProviderKind
class OllamaAdapter(OpenAICompatibleAdapter): protocol="ollama"
class LocalOpenAIAdapter(OpenAICompatibleAdapter): protocol="openai-compatible"
class NativeOpenAIAdapter(OpenAICompatibleAdapter): protocol="openai"
class OpenRouterAdapter(OpenAICompatibleAdapter): protocol="openrouter"
def adapter_for(config:ProviderConfig, **kwargs):
    cls={ProviderKind.OLLAMA:OllamaAdapter,ProviderKind.LOCAL_OPENAI:LocalOpenAIAdapter,ProviderKind.OPENAI:NativeOpenAIAdapter,ProviderKind.OPENROUTER:OpenRouterAdapter}[config.kind]
    return cls(config,**kwargs)
