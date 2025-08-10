# Harmony Response Format Parser

This repository now includes a comprehensive parser for OpenAI's gpt-oss harmony response format. The harmony format uses special tokens to structure AI responses with roles, channels, and tool calls.

## Features

The harmony parser supports:

- **Special Tokens**: Parse messages with `<|start|>`, `<|end|>`, `<|message|>`, `<|channel|>`, `<|constrain|>`, `<|return|>`, and `<|call|>`
- **Message Structure**: Handle the format `<|start|>{header}<|message|>{content}<|end|>`
- **Roles**: Support for system, developer, user, assistant, and tool roles
- **Channels**: Parse assistant messages with different channels (final, analysis, commentary)
- **Tool Calls**: Handle function calling with recipients and constraints
- **Reasoning Output**: Separate chain-of-thought (analysis channel) from final responses
- **Built-in Tools**: Support for browser and python tool calls

## Usage

### Basic Integration

The harmony parser is integrated into the main `lm-chat.py` script:

```bash
# Enable harmony parsing mode
python3 lm-chat.py run --harmony hf.co/ggml-org/gpt-oss-20b-gguf

# Use with a prompt
python3 lm-chat.py run --harmony hf.co/ggml-org/gpt-oss-20b-gguf "What's the weather like?"
```

### Standalone Usage

You can also use the harmony parser as a standalone module:

```python
from harmony_parser import HarmonyParser

# Create parser instance
parser = HarmonyParser()

# Parse harmony-formatted text
harmony_text = '''<|start|>role:user<|message|>Hello!<|end|>
<|start|>role:assistant,channel:final<|message|>Hi there!<|end|>'''

messages = parser.parse_conversation(harmony_text)

# Extract different types of content
user_facing = parser.extract_user_facing(messages)
reasoning = parser.extract_reasoning(messages)
tool_calls = parser.extract_tool_calls(messages)

# Format for display
display_text = parser.format_for_display(messages, include_reasoning=True)
print(display_text)
```

### Example Scenarios

The parser handles various harmony format scenarios:

#### 1. Basic Chat with Reasoning

```
<|start|>role:user<|message|>What's the weather like in Tokyo?<|end|>

<|start|>role:assistant,channel:analysis<|message|>The user is asking about weather in Tokyo. I should use a weather tool to get current information.<|end|>

<|start|>role:assistant,channel:final<|message|>I'll check the current weather in Tokyo for you. <|call|>weather<|{"location": "Tokyo, Japan"}|><|end|>
```

#### 2. Tool Calls with Built-in Tools

```
<|start|>role:assistant,channel:final<|message|>I'll search for recent AI news.

<|call|>browser<|{"action": "search", "query": "recent AI developments"}|><|end|>

<|start|>role:assistant,channel:final<|message|>Let me calculate that for you.

<|call|>python<|{"code": "import math\nprint(math.factorial(10))"}|><|end|>
```

#### 3. Constrained Responses

```
<|start|>role:system<|message|><|constrain|>Respond only with facts, no opinions<|return|>You are a helpful assistant.<|end|>

<|start|>role:assistant,channel:final<|message|>Python is a programming language created by Guido van Rossum in 1991.<|end|>
```

## API Reference

### HarmonyParser Class

#### Methods

- `parse_conversation(text: str) -> List[HarmonyMessage]`: Parse complete harmony-formatted conversation
- `extract_reasoning(messages) -> List[HarmonyMessage]`: Extract reasoning messages (analysis channel)
- `extract_user_facing(messages) -> List[HarmonyMessage]`: Extract user-facing messages
- `extract_tool_calls(messages) -> List[Dict]`: Extract all tool calls
- `format_for_display(messages, include_reasoning=False) -> str`: Format for display

### HarmonyMessage Class

#### Properties

- `role`: Message role (Role enum)
- `content`: Clean message content
- `channel`: Message channel (Channel enum, optional)
- `recipient`: Message recipient (optional)
- `tool_calls`: List of tool calls in the message
- `constraints`: List of constraints applied to the message
- `raw_content`: Original raw message content

#### Methods

- `is_reasoning() -> bool`: Check if message contains reasoning
- `is_user_facing() -> bool`: Check if message is user-facing

### Enums

- **Role**: SYSTEM, DEVELOPER, USER, ASSISTANT, TOOL
- **Channel**: FINAL, ANALYSIS, COMMENTARY
- **SpecialToken**: START, END, MESSAGE, CHANNEL, CONSTRAIN, RETURN, CALL

## Examples

Run the example scripts to see the parser in action:

```bash
# Run comprehensive examples
python3 harmony_examples.py

# Run integration tests
python3 test_harmony_integration.py
```

## Error Handling

The parser is designed to be robust:

- Malformed messages are ignored
- Invalid JSON in tool calls is stored as raw text
- Missing channels/recipients are handled gracefully
- Empty or non-harmony text returns empty results

## Integration with lm-chat.py

When `--harmony` flag is used, the chat client will:

1. Parse incoming streaming responses for harmony format
2. Display user-facing content prominently
3. Show reasoning chain separately
4. List extracted tool calls with parameters
5. Maintain backward compatibility with standard responses

This enhancement makes lm-chat.py compatible with OpenAI's gpt-oss models while preserving existing functionality for other models.