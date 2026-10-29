# LLM Provider Abstraction Layer Design

## Problem Statement

Building a Discord bot fleet that works with Claude today, but might need to switch to GPT, Gemini, or local models in the future. We need an architecture that allows switching LLM providers without rewriting application code.

## Solution: Three-Layer Architecture

### Layer 1: Unified Interface (Model-Agnostic)

All LLM providers implement the same interface:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Unified message format (model-independent)"""
    role: str  # "user", "assistant", "system"
    content: str

    def to_dict(self) -> Dict[str, str]:
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
```

### Layer 2: Concrete Implementations

#### ClaudeProvider (Current)
```python
class ClaudeProvider(LLMProvider):
    """Anthropic Claude implementation"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        formatted_messages = [msg.to_dict() for msg in messages]
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=min(max_tokens, 4096),
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
```

#### OpenAIProvider (Ready for future)
```python
class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        formatted_messages.extend([msg.to_dict() for msg in messages])
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=min(max_tokens, 8192)
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
```

#### GeminiProvider (Easy to add)
```python
class GeminiProvider(LLMProvider):
    """Google Gemini implementation"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
    
    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        # Implementation details...
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "google",
            "model": self.model,
            "max_tokens": 8000
        }
```

#### LocalModelProvider (Support local inference)
```python
class LocalModelProvider(LLMProvider):
    """Support local models (Ollama, vLLM, etc.)"""
    
    def __init__(self, base_url: str, model: str):
        import requests
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    def send_message(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
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
            "base_url": self.base_url
        }
```

### Layer 3: Factory Pattern

```python
class LLMFactory:
    """Create LLM provider instances"""
    
    _providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "local": LocalModelProvider,
    }
    
    @staticmethod
    def create(
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create LLM provider instance
        
        Usage:
            # Claude
            llm = LLMFactory.create("claude", api_key="sk-...")
            
            # OpenAI
            llm = LLMFactory.create("openai", api_key="sk-...")
            
            # Local
            llm = LLMFactory.create("local", base_url="http://localhost:8000", model="llama2")
        """
        if provider_name not in LLMFactory._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = LLMFactory._providers[provider_name]
        
        if provider_name == "local":
            return provider_class(base_url=kwargs["base_url"], model=model or "llama2")
        elif model:
            return provider_class(api_key=api_key, model=model)
        else:
            return provider_class(api_key=api_key)
    
    @staticmethod
    def register(provider_name: str, provider_class: type):
        """Register new LLM provider"""
        LLMFactory._providers[provider_name] = provider_class
```

## Application Layer (Completely Model-Independent)

### Lambda Function Example

```python
# lambda/omp_agent_handler.py

from llm_provider import LLMFactory, LLMMessage, LLMConfig
import json
import boto3


def lambda_handler(event, context):
    """Handle message to agent"""
    
    agent_id = event['agent_id']
    user_message = event['message']
    thread_id = event['thread_id']
    
    # 1. Get this agent's LLM configuration from DynamoDB
    llm_config = LLMConfig.from_dynamodb(agent_id)
    
    # 2. Create LLM instance (automatically uses this agent's model)
    llm = llm_config.get_provider()
    
    # 3. Get conversation history
    session_state = get_session_from_dynamodb(thread_id, agent_id)
    messages = [
        LLMMessage(role=msg['role'], content=msg['content'])
        for msg in session_state['messages']
    ]
    
    # 4. Get agent's system prompt
    system_prompt = get_agent_persona(agent_id)
    
    # 5. Call LLM (completely model-agnostic!)
    reply = llm.send_message(
        messages=messages + [LLMMessage(role='user', content=user_message)],
        system_prompt=system_prompt,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens
    )
    
    # 6. Save conversation history
    session_state['messages'].append(
        {"role": "user", "content": user_message}
    )
    session_state['messages'].append(
        {"role": "assistant", "content": reply}
    )
    save_session_to_dynamodb(thread_id, agent_id, session_state)
    
    # 7. Return reply
    return {
        'statusCode': 200,
        'reply': reply,
        'llm_provider': llm_config.provider,
        'llm_model': llm_config.model
    }
```

### Configuration Management

```python
# config.py

import os
import boto3
from typing import Optional


class LLMConfig:
    """LLM configuration management"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "claude")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", None)
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    
    def get_provider(self) -> LLMProvider:
        """Get configured LLM provider"""
        return LLMFactory.create(
            provider_name=self.provider,
            api_key=self.api_key,
            model=self.model
        )
    
    @staticmethod
    def from_dynamodb(agent_id: str) -> "LLMConfig":
        """Load agent-specific LLM config from DynamoDB"""
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('discord-fleet-agents')
        
        response = table.get_item(Key={'agent_id': agent_id})
        agent_config = response.get('Item', {})
        
        config = LLMConfig()
        config.provider = agent_config.get('llm_provider', 'claude')
        config.model = agent_config.get('llm_model', 'claude-3-5-sonnet-20241022')
        config.temperature = agent_config.get('temperature', 0.7)
        config.max_tokens = agent_config.get('max_tokens', 1024)
        config.api_key = os.getenv("LLM_API_KEY")
        
        return config
```

## Model Switching Cost Analysis

### Without Abstraction Layer
```python
# ❌ Bad: Code tightly coupled to specific LLM
from anthropic import Anthropic
from openai import OpenAI

client = Anthropic(api_key=key)
response = client.messages.create(...)

# Want to switch? Rewrite 100+ places in code ❌
```

### With Abstraction Layer
```python
# ✅ Good: Model-independent code
llm = LLMFactory.create("claude")     # Use Claude
response = llm.send_message(messages)

# Want to switch? Change ONE line! ✅
llm = LLMFactory.create("openai")     # Use GPT
response = llm.send_message(messages)  # Same code!
```

## DynamoDB Schema

### discord-fleet-agents Table

```json
{
  "agent_id": "writing-assistant",  (PK)
  "agent_name": "Writing Assistant",
  "system_prompt": "You are a professional writing editor...",
  
  // LLM Configuration
  "llm_provider": "claude",
  "llm_model": "claude-3-5-sonnet-20241022",
  "temperature": 0.7,
  "max_tokens": 1024,
  "cost_limit": 100,  (optional: monthly cost limit)
  
  // Metadata
  "created_at": "2026-10-29T23:30:00Z",
  "updated_at": "2026-10-29T23:30:00Z",
  "created_by": "user_id"
}
```

### discord-fleet-sessions Table

```json
{
  "thread_id": "thread-123",         (PK)
  "agent_id": "writing-assistant",   (SK)
  
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  
  "created_at": "2026-10-29T23:30:00Z",
  "updated_at": "2026-10-29T23:30:00Z",
  "user_id": "user-123",
  "channel_id": "channel-456",
  
  // TTL: Auto-delete after 30 days
  "ttl": 1730000000
}
```

## Advanced Features

### Multi-Model Voting

```python
class LLMEnsemble(LLMProvider):
    """Get responses from multiple models, vote on best"""
    
    def __init__(self, providers: List[LLMProvider]):
        self.providers = providers
    
    def send_message(self, messages, **kwargs) -> str:
        responses = [
            provider.send_message(messages, **kwargs)
            for provider in self.providers
        ]
        
        # Select best response (by length, logic, etc.)
        best = select_best_response(responses)
        return best
```

### Automatic Failover

```python
def get_llm_with_fallback(primary: str, fallback: str):
    """Try primary, fall back to secondary if error"""
    try:
        llm = LLMFactory.create(primary)
        llm.get_model_info()  # Test connection
        return llm
    except Exception:
        return LLMFactory.create(fallback)
```

### Cost-Based Selection

```python
def select_model_by_cost(complexity: str, budget: float):
    """Choose model based on question complexity and budget"""
    
    if complexity == "simple" and budget < 1:
        return LLMFactory.create("gemini")  # Cheapest
    elif complexity == "medium":
        return LLMFactory.create("openai")  # Balanced
    else:
        return LLMFactory.create("claude")  # Most powerful
```

## Adding New Model Support (Step-by-Step)

### To add a new LLM provider:

1. **Create new class inheriting from LLMProvider**
```python
class NewModelProvider(LLMProvider):
    def send_message(self, messages, **kwargs):
        # Implement API calls
        pass
    
    def get_model_info(self):
        # Return metadata
        pass
```

2. **Register with factory**
```python
LLMFactory.register("new-model", NewModelProvider)
```

3. **Use it**
```python
llm = LLMFactory.create("new-model", api_key=key)
response = llm.send_message(messages)
```

**Rest of application code: NO CHANGES! ✅**

## Principle: Inversion of Dependency

Bad (Tightly Coupled):
```
Application Code → Claude API
Application Code → OpenAI API
Application Code → Gemini API
(lots of conditional logic)
```

Good (Loosely Coupled via Abstraction):
```
Application Code ↘
                  → LLMProvider Interface ↘
                                          → Claude Implementation
                                          → OpenAI Implementation
                                          → Gemini Implementation
(application code is clean & model-agnostic)
```

## Summary

- **Layer 1:** Unified interface (all models implement same methods)
- **Layer 2:** Concrete implementations (one per model)
- **Layer 3:** Application code (completely model-independent)
- **Factory:** Easy instantiation & registration

This design allows you to:
- Switch models with one-line change ✅
- Add new models without touching application code ✅
- Support multiple models simultaneously ✅
- Implement advanced features (voting, failover, cost optimization) ✅

**Result: Future-proof architecture!** 🚀
