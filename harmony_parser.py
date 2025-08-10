#!/usr/bin/env python3
"""
Harmony Response Format Parser for OpenAI's gpt-oss models.

This module provides functionality to parse the harmony response format which uses
special tokens to structure messages with roles, channels, and tool calls.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class Role(Enum):
    """Message roles supported in harmony format."""
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Channel(Enum):
    """Assistant message channels."""
    FINAL = "final"
    ANALYSIS = "analysis"
    COMMENTARY = "commentary"


class SpecialToken(Enum):
    """Special tokens used in harmony format."""
    START = "<|start|>"
    END = "<|end|>"
    MESSAGE = "<|message|>"
    CHANNEL = "<|channel|>"
    CONSTRAIN = "<|constrain|>"
    RETURN = "<|return|>"
    CALL = "<|call|>"


@dataclass
class HarmonyMessage:
    """Represents a parsed harmony format message."""
    role: Role
    content: str
    channel: Optional[Channel] = None
    recipient: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    raw_content: str = ""
    
    def is_reasoning(self) -> bool:
        """Check if this message contains reasoning (analysis channel)."""
        return self.channel == Channel.ANALYSIS
    
    def is_user_facing(self) -> bool:
        """Check if this message is user-facing (final channel or no channel)."""
        return self.channel in [Channel.FINAL, None] and self.role != Role.TOOL


@dataclass
class ToolCall:
    """Represents a tool call within a harmony message."""
    name: str
    parameters: Dict[str, Any]
    recipient: Optional[str] = None
    constraints: List[str] = field(default_factory=list)


class HarmonyParser:
    """Parser for OpenAI harmony response format."""
    
    def __init__(self):
        self.special_tokens = [token.value for token in SpecialToken]
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for parsing."""
        # Pattern to match complete messages
        self.message_pattern = re.compile(
            r'<\|start\|>(.*?)<\|message\|>(.*?)<\|end\|>',
            re.DOTALL
        )
        
        # Pattern to extract role from header
        self.role_pattern = re.compile(r'role:(\w+)')
        
        # Pattern to extract channel from header
        self.channel_pattern = re.compile(r'channel:(\w+)')
        
        # Pattern to extract recipient from header
        self.recipient_pattern = re.compile(r'recipient:([^\s,]+)')
        
        # Pattern to match tool calls
        self.tool_call_pattern = re.compile(
            r'<\|call\|>([^<]+?)<\|([^<]+?)\|>',
            re.DOTALL
        )
        
        # Pattern to match constraints
        self.constraint_pattern = re.compile(
            r'<\|constrain\|>([^<]+)<\|return\|>',
            re.DOTALL
        )
    
    def parse_conversation(self, text: str) -> List[HarmonyMessage]:
        """
        Parse a complete harmony-formatted conversation.
        
        Args:
            text: Raw harmony-formatted text
            
        Returns:
            List of parsed HarmonyMessage objects
        """
        messages = []
        
        # Find all complete messages
        for match in self.message_pattern.finditer(text):
            header = match.group(1).strip()
            content = match.group(2).strip()
            
            message = self._parse_single_message(header, content)
            if message:
                message.raw_content = match.group(0)
                messages.append(message)
        
        return messages
    
    def _parse_single_message(self, header: str, content: str) -> Optional[HarmonyMessage]:
        """Parse a single message from header and content."""
        # Extract role
        role_match = self.role_pattern.search(header)
        if not role_match:
            return None
        
        try:
            role = Role(role_match.group(1).lower())
        except ValueError:
            return None
        
        # Extract channel (optional)
        channel = None
        channel_match = self.channel_pattern.search(header)
        if channel_match:
            try:
                channel = Channel(channel_match.group(1).lower())
            except ValueError:
                pass
        
        # Extract recipient (optional)
        recipient = None
        recipient_match = self.recipient_pattern.search(header)
        if recipient_match:
            recipient = recipient_match.group(1)
        
        # Parse tool calls and constraints from content
        tool_calls = self._parse_tool_calls(content)
        constraints = self._parse_constraints(content)
        
        # Clean content by removing tool calls and constraints
        clean_content = self._clean_content(content)
        
        return HarmonyMessage(
            role=role,
            content=clean_content,
            channel=channel,
            recipient=recipient,
            tool_calls=tool_calls,
            constraints=constraints
        )
    
    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from message content."""
        tool_calls = []
        
        for match in self.tool_call_pattern.finditer(content):
            tool_name = match.group(1).strip()
            params_text = match.group(2).strip()
            
            # Try to parse parameters as JSON
            try:
                if params_text.startswith('{') and params_text.endswith('}'):
                    parameters = json.loads(params_text)
                elif params_text.startswith('"') and params_text.endswith('"'):
                    # Handle JSON string that needs parsing
                    json_string = json.loads(params_text)
                    if isinstance(json_string, str) and json_string.startswith('{'):
                        parameters = json.loads(json_string)
                    else:
                        parameters = {"value": json_string}
                else:
                    # Handle simple key=value format
                    parameters = self._parse_simple_params(params_text)
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, store as raw string
                parameters = {"raw": params_text}
            
            tool_calls.append({
                "name": tool_name,
                "parameters": parameters
            })
        
        return tool_calls
    
    def _parse_constraints(self, content: str) -> List[str]:
        """Parse constraints from message content."""
        constraints = []
        
        for match in self.constraint_pattern.finditer(content):
            constraint = match.group(1).strip()
            constraints.append(constraint)
        
        return constraints
    
    def _parse_simple_params(self, params_text: str) -> Dict[str, str]:
        """Parse simple key=value parameter format."""
        params = {}
        for part in params_text.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.strip()] = value.strip().strip('"').strip("'")
        return params
    
    def _clean_content(self, content: str) -> str:
        """Remove tool calls and constraints from content, leaving only text."""
        # Remove tool calls
        content = self.tool_call_pattern.sub('', content)
        
        # Remove constraints
        content = self.constraint_pattern.sub('', content)
        
        # Clean up extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def extract_reasoning(self, messages: List[HarmonyMessage]) -> List[HarmonyMessage]:
        """Extract reasoning messages (analysis channel) from a conversation."""
        return [msg for msg in messages if msg.is_reasoning()]
    
    def extract_user_facing(self, messages: List[HarmonyMessage]) -> List[HarmonyMessage]:
        """Extract user-facing messages from a conversation."""
        return [msg for msg in messages if msg.is_user_facing()]
    
    def extract_tool_calls(self, messages: List[HarmonyMessage]) -> List[Dict[str, Any]]:
        """Extract all tool calls from a conversation."""
        tool_calls = []
        for message in messages:
            for tool_call in message.tool_calls:
                tool_calls.append({
                    "message_role": message.role.value,
                    "message_channel": message.channel.value if message.channel else None,
                    "tool_name": tool_call["name"],
                    "parameters": tool_call["parameters"]
                })
        return tool_calls
    
    def format_for_display(self, messages: List[HarmonyMessage], 
                          include_reasoning: bool = False) -> str:
        """Format messages for display, optionally including reasoning."""
        output = []
        
        for message in messages:
            if not include_reasoning and message.is_reasoning():
                continue
            
            role_display = message.role.value.capitalize()
            if message.channel:
                role_display += f" ({message.channel.value})"
            
            if message.recipient:
                role_display += f" -> {message.recipient}"
            
            output.append(f"{role_display}: {message.content}")
            
            # Add tool calls if present
            for tool_call in message.tool_calls:
                output.append(f"  Tool Call: {tool_call['name']}")
                if tool_call['parameters']:
                    output.append(f"    Parameters: {tool_call['parameters']}")
        
        return "\n\n".join(output)


def create_harmony_example() -> str:
    """Create an example harmony-formatted conversation."""
    return '''<|start|>role:user<|message|>What's the weather like in Tokyo?<|end|>

<|start|>role:assistant,channel:analysis<|message|>The user is asking about weather in Tokyo. I should use a weather tool to get current information.<|end|>

<|start|>role:assistant,channel:final<|message|>I'll check the current weather in Tokyo for you. <|call|>weather<|{"location": "Tokyo, Japan"}|><|end|>

<|start|>role:tool<|message|>{"temperature": "22°C", "condition": "Partly cloudy", "humidity": "65%"}<|end|>

<|start|>role:assistant,channel:final<|message|>The current weather in Tokyo is 22°C and partly cloudy with 65% humidity.<|end|>'''


def create_browser_tool_example() -> str:
    """Create an example with browser tool usage."""
    return '''<|start|>role:user<|message|>Can you search for recent news about AI developments?<|end|>

<|start|>role:assistant,channel:analysis<|message|>I need to search for recent AI news. I'll use the browser tool to search for this information.<|end|>

<|start|>role:assistant,channel:final<|message|>I'll search for recent AI development news for you.

<|call|>browser<|{"action": "search", "query": "recent AI developments news 2024"}|><|end|>

<|start|>role:tool<|message|>Found several recent articles about AI developments including breakthroughs in LLMs and robotics.<|end|>

<|start|>role:assistant,channel:final<|message|>Here are some recent AI developments I found:
- New breakthrough in large language model efficiency
- Advances in AI robotics applications  
- Progress in AI safety research<|end|>'''


def create_python_tool_example() -> str:
    """Create an example with python tool usage."""
    return '''<|start|>role:user<|message|>Calculate the factorial of 10<|end|>

<|start|>role:assistant,channel:analysis<|message|>I need to calculate 10! which is 10 factorial. I can use Python to compute this.<|end|>

<|start|>role:assistant,channel:final<|message|>I'll calculate the factorial of 10 using Python.

<|call|>python<|{"code": "import math\nresult = math.factorial(10)\nprint(f'10! = {result}')"}|><|end|>

<|start|>role:tool<|message|>10! = 3628800<|end|>

<|start|>role:assistant,channel:final<|message|>The factorial of 10 is 3,628,800.<|end|>'''


def create_constrained_example() -> str:
    """Create an example with constraints."""
    return '''<|start|>role:system<|message|><|constrain|>Respond only with facts, no opinions<|return|>You are a helpful assistant that provides factual information.<|end|>

<|start|>role:user<|message|>Tell me about Python programming<|end|>

<|start|>role:assistant,channel:analysis<|message|>The user wants information about Python. I need to provide only factual information as per the constraint.<|end|>

<|start|>role:assistant,channel:final<|message|>Python is a high-level programming language created by Guido van Rossum and first released in 1991. It emphasizes code readability and uses significant whitespace. Python supports multiple programming paradigms including procedural, object-oriented, and functional programming.<|end|>'''