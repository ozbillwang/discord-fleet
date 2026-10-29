# LLM Model Switching - Quick Reference

## The Problem You Might Face

> What if we need to switch from Claude to GPT in the future? Do I need to rewrite everything?

## The Answer

✅ **NO! You'll NEVER need to rewrite your code!**

## Why? Abstraction Layer

```python
# Without abstraction layer (BAD):
from anthropic import Anthropic
response = Anthropic().messages.create(model="claude-3-5-sonnet-20241022", ...)
# To switch to GPT? Rewrite 100+ places ❌

# With abstraction layer (GOOD):
llm = LLMFactory.create("claude")
response = llm.send_message(messages)

# To switch to GPT? Change ONE line:
llm = LLMFactory.create("openai")
response = llm.send_message(messages)  # Identical code! ✅
```

## Three Ways to Switch Models

### Method 1: Environment Variable (Zero Code Changes)

```bash
# Current: Using Claude
export LLM_PROVIDER="claude"
export LLM_API_KEY="sk-ant-..."

# Switch to GPT: Change only these
export LLM_PROVIDER="openai"
export LLM_API_KEY="sk-..."

# Redeploy Lambda
sam deploy

# Done! No code changes at all! ✅
```

### Method 2: Database Configuration (Fine-Grained Control)

```python
# DynamoDB discord-fleet-agents table

# Agent 1: Uses Claude
{
  "agent_id": "writing-assistant",
  "llm_provider": "claude",
  "llm_model": "claude-3-5-sonnet-20241022"
}

# Agent 2: Uses OpenAI
{
  "agent_id": "code-reviewer",
  "llm_provider": "openai",
  "llm_model": "gpt-4o"
}

# Agent 3: Uses Gemini
{
  "agent_id": "translator",
  "llm_provider": "gemini",
  "llm_model": "gemini-2.0-flash"
}

# Lambda code:
llm_config = LLMConfig.from_dynamodb(agent_id)
llm = llm_config.get_provider()
response = llm.send_message(messages)  # Auto uses agent's model!
```

### Method 3: Runtime Selection (A/B Testing)

```python
# Route based on complexity
def select_model(complexity: str):
    if complexity == "simple":
        return LLMFactory.create("gemini")      # Cheap
    elif complexity == "medium":
        return LLMFactory.create("openai")      # Balanced
    else:
        return LLMFactory.create("claude")      # Powerful

llm = select_model(analyze_complexity(messages))
response = llm.send_message(messages)
```

## Cost Comparison: With vs Without Abstraction

| Operation | Without Abstraction | With Abstraction |
|-----------|-------|-----|
| Switch all agents to GPT | Rewrite 100+ places ❌ | Change 1 line ✅ |
| Different agents use different models | Complex conditional logic ❌ | Database config ✅ |
| Add support for new model | Modify all call sites ❌ | Write 1 new class ✅ |
| A/B test two models | Hard to control ❌ | Simple config ✅ |
| Automatic failover | Catch/retry everywhere ❌ | Wrapper function ✅ |
| Cost optimization (cheaper model for simple tasks) | Complex routing ❌ | Rule-based selection ✅ |

## Supported Providers (And Easy to Add)

```python
# Current providers (ready to use):
llm = LLMFactory.create("claude")           # ✅ Works now
llm = LLMFactory.create("openai")           # ✅ Works now
llm = LLMFactory.create("gemini")           # ✅ Works now
llm = LLMFactory.create("local", base_url="http://localhost:8000")  # ✅ Works now

# Add a new provider? Write 1 class (1-2 hours):
class NewModelProvider(LLMProvider):
    def send_message(self, messages, **kwargs):
        # Implement your model API calls
        pass

LLMFactory.register("new-model", NewModelProvider)
llm = LLMFactory.create("new-model")  # Done! ✅
```

## Real-World Scenarios

### Scenario: Claude API Gets Expensive
```bash
# Old way: Rewrite application code ❌
# New way: Change config, redeploy ✅

export LLM_PROVIDER="openai"
sam deploy
```

### Scenario: Gemini Releases Game-Changing Feature
```bash
# Old way: Risky, requires code changes ❌
# New way: Easy A/B test ✅

# Test with 10% traffic on Gemini
def get_llm():
    if random.random() < 0.1:
        return LLMFactory.create("gemini")
    else:
        return LLMFactory.create("claude")
```

### Scenario: Run Local Model for Cost Savings
```bash
# Old way: Major refactoring ❌
# New way: Add provider + update config ✅

llm = LLMFactory.create("local", base_url="http://localhost:8000", model="llama2")
response = llm.send_message(messages)  # Identical call!
```

### Scenario: Need Redundancy (Fallback)
```python
def get_llm_with_fallback():
    try:
        llm = LLMFactory.create("claude")
        llm.get_model_info()  # Test connection
        return llm
    except:
        return LLMFactory.create("openai")  # Automatic fallback

llm = get_llm_with_fallback()
response = llm.send_message(messages)  # Works with either provider!
```

## Adding a New Model Provider (Step-by-Step)

### Step 1: Create Provider Class (30 minutes)
```python
class MyCustomProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    def send_message(self, messages, system_prompt=None, **kwargs):
        # Call your model API
        ...
    
    def get_model_info(self):
        return {"provider": "my-model", "max_tokens": 2048}
```

### Step 2: Register (1 minute)
```python
LLMFactory.register("my-model", MyCustomProvider)
```

### Step 3: Use (No changes to existing code!)
```python
llm = LLMFactory.create("my-model", api_key="...")
response = llm.send_message(messages)  # Works!
```

**Entire application: NO CHANGES!** ✅

## Core Design Principles

### DO ✅
```python
# Call through abstraction
llm = LLMFactory.create(provider_name)
response = llm.send_message(messages)

# Config in database/environment
# One class per provider
# Factory for creation
```

### DON'T ❌
```python
# Don't: Direct API calls
from anthropic import Anthropic
response = Anthropic().messages.create(...)

# Don't: Conditional logic scattered everywhere
if provider == "claude":
    ...
elif provider == "openai":
    ...

# Don't: Hardcode model selection
```

## Future-Proofing Checklist

- [ ] Use LLMFactory, not direct API calls
- [ ] Config in DynamoDB, not hardcoded
- [ ] One provider class per model type
- [ ] Application code calls through abstraction only
- [ ] Test with multiple providers during development

## FAQ

### Q: Will this add performance overhead?
**A:** No. It's just one extra function call (<1% impact).

### Q: Will application code need to change?
**A:** No. The abstraction layer is completely transparent.

### Q: Can I use multiple models at once?
**A:** Yes! Create different LLM instances for different purposes.

### Q: What if my model API is weird?
**A:** Write a custom provider class that implements LLMProvider.

### Q: Is this production-ready?
**A:** Yes! It's a standard design pattern used by major frameworks.

## Key Takeaway

```
OLD WAY:
  Application tightly coupled to specific LLM
  → Switching models = code rewrite ❌

NEW WAY:
  Abstraction layer between application and LLM
  → Switching models = config change ✅
  
COST: 1-2 days to implement
BENEFIT: Switch ANY model ANYTIME without code changes
ROI: Infinite! 🚀
```

## Summary

| Aspect | Benefit |
|--------|---------|
| **Flexibility** | Switch models with one line/config |
| **Future-proof** | Add any new model without touching application code |
| **Testability** | Easy to mock or swap models in tests |
| **Maintenance** | Centralized LLM logic, easier to update |
| **Cost** | Optimize by using cheaper models when appropriate |
| **Reliability** | Implement failover easily |

**Result: Bulletproof, future-ready architecture!** 🛡️✅
