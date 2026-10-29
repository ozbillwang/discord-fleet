"""
Discord Fleet - LLM Provider Abstraction Layer

Supports multiple LLM providers (Claude, OpenAI, Gemini, Local models)
Application code remains completely model-agnostic.

Usage:
    llm = LLMFactory.create("claude", api_key="sk-...")
    response = llm.send_message(messages, system_prompt="You are...")
    
    # Switch to OpenAI (change ONE line only):
    llm = LLMFactory.create("openai", api_key="sk-...")
    response = llm.send_message(messages, system_prompt="You are...")
    # Rest of code unchanged!
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os


@dataclass
class LLMMessage:
    """Unified message format (model-independent)"""
    role: str  # "user", "assistant", "system"
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format"""
        return {"role": self.role, "content": self.content}


class LLMProvider(ABC):
    """Base class for all LLM providers"""

    @abstractmethod
    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Send message to LLM, return text response

        Args:
            messages: Message list (excluding system_prompt)
            system_prompt: System instruction (if any)
            temperature: Randomness (0.0-2.0)
            max_tokens: Maximum output length

        Returns:
            LLM's text response
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata"""
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude implementation"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude provider

        Args:
            api_key: Anthropic API key
            model: Claude model name (default: claude-3-5-sonnet)
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Call Claude API"""

        formatted_messages = [msg.to_dict() for msg in messages]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=min(max_tokens, 4096),  # Claude limit
            system=system_prompt or "",
            messages=formatted_messages,
            temperature=temperature
        )

        return response.content[0].text

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "model": self.model,
            "max_tokens": 4096,
            "supports_vision": True,
            "supports_function_calling": True
        }


class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install openai: pip install openai")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Call OpenAI API"""

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        formatted_messages.extend([msg.to_dict() for msg in messages])

        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=min(max_tokens, 8192)  # OpenAI limit
        )

        return response.choices[0].message.content

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model,
            "max_tokens": 8192,
            "supports_vision": True,
            "supports_function_calling": True
        }


class GeminiProvider(LLMProvider):
    """Google Gemini implementation"""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini provider

        Args:
            api_key: Google API key
            model: Model name (default: gemini-2.0-flash)
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install required packages: pip install google-generativeai")

        self.api_key = api_key
        self.model = model

    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Call Gemini API"""
        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        formatted_messages = [msg.to_dict() for msg in messages]

        response = client.messages.create(
            model=self.model,
            messages=formatted_messages,
            max_tokens=min(max_tokens, 8000),
            temperature=temperature,
            system=system_prompt or ""
        )

        return response.content[0].text

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "google",
            "model": self.model,
            "max_tokens": 8000,
            "supports_vision": True,
            "supports_function_calling": False
        }


class LocalModelProvider(LLMProvider):
    """Support for local models (Ollama, vLLM, etc.)"""

    def __init__(self, base_url: str, model: str):
        """
        Initialize local model provider

        Args:
            base_url: Local model server URL (e.g., http://localhost:8000)
            model: Model name (e.g., llama2, mistral)
        """
        try:
            import requests
        except ImportError:
            raise ImportError("Install requests: pip install requests")

        self.base_url = base_url.rstrip("/")
        self.model = model

    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Call local model API (assumes OpenAI-compatible endpoint)"""
        import requests

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        formatted_messages.extend([msg.to_dict() for msg in messages])

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": formatted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "local",
            "model": self.model,
            "base_url": self.base_url,
            "max_tokens": 4096,
            "supports_vision": False,
            "supports_function_calling": False
        }


class LLMFactory:
    """Factory for creating LLM provider instances"""

    _providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "local": LocalModelProvider,
    }

    @staticmethod
    def register(provider_name: str, provider_class: type):
        """
        Register new LLM provider

        Args:
            provider_name: Name to use with create()
            provider_class: Must inherit from LLMProvider
        """
        if not issubclass(provider_class, LLMProvider):
            raise TypeError(f"{provider_class} must inherit from LLMProvider")
        LLMFactory._providers[provider_name] = provider_class

    @staticmethod
    def create(
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create LLM provider instance

        Args:
            provider_name: Provider name ("claude", "openai", "gemini", "local", etc.)
            api_key: API key (if None, reads from LLM_API_KEY env var)
            model: Model name (optional, uses default if not specified)
            **kwargs: Additional arguments (e.g., base_url for local models)

        Returns:
            LLMProvider instance

        Examples:
            # Claude
            llm = LLMFactory.create("claude", api_key="sk-ant-...")
            
            # OpenAI
            llm = LLMFactory.create("openai", api_key="sk-...", model="gpt-4")
            
            # Local model
            llm = LLMFactory.create("local", base_url="http://localhost:8000", model="llama2")
            
            # From environment variables
            llm = LLMFactory.create("claude")  # Reads LLM_API_KEY env var
        """

        if provider_name not in LLMFactory._providers:
            available = ", ".join(LLMFactory._providers.keys())
            raise ValueError(
                f"Unknown provider: {provider_name}\n"
                f"Available providers: {available}"
            )

        provider_class = LLMFactory._providers[provider_name]

        # Read API key from environment if not provided
        if api_key is None and provider_name != "local":
            api_key = os.getenv("LLM_API_KEY")
            if api_key is None:
                raise ValueError(
                    f"API key missing. Provide api_key parameter or set LLM_API_KEY env var"
                )

        # Create instance based on provider type
        if provider_name == "local":
            base_url = kwargs.get("base_url")
            if not base_url:
                raise ValueError("Local model requires base_url parameter")
            return provider_class(base_url=base_url, model=model or "llama2")

        elif model:
            return provider_class(api_key=api_key, model=model)
        else:
            return provider_class(api_key=api_key)

    @staticmethod
    def list_providers() -> Dict[str, type]:
        """List all registered providers"""
        return dict(LLMFactory._providers)


# Usage Examples
if __name__ == "__main__":
    # Example 1: Claude
    print("=" * 60)
    print("Example 1: Using Claude")
    print("=" * 60)
    
    llm = LLMFactory.create("claude", api_key="sk-ant-YOUR_KEY")
    print(f"Claude model info: {llm.get_model_info()}\n")
    
    # Example 2: Switch to OpenAI (only change provider name!)
    print("=" * 60)
    print("Example 2: Switch to OpenAI (code is identical!)")
    print("=" * 60)
    
    llm = LLMFactory.create("openai", api_key="sk-YOUR_KEY")
    print(f"OpenAI model info: {llm.get_model_info()}\n")
    
    # Example 3: List available providers
    print("=" * 60)
    print("Available Providers:")
    print("=" * 60)
    for name in LLMFactory.list_providers().keys():
        print(f"  - {name}")
    
    print("\n✅ All providers use the SAME API interface!")
    print("✅ Switch models by changing ONE line of code!")
