#!/usr/bin/env python3
"""
Comprehensive validation test for the harmony parser implementation.

This script validates that all requirements from the problem statement are met.
"""

from harmony_parser import (
    HarmonyParser, Role, Channel, SpecialToken, HarmonyMessage,
    create_harmony_example, create_browser_tool_example, 
    create_python_tool_example, create_constrained_example
)

def test_special_tokens():
    """Test that all required special tokens are supported."""
    print("Testing Special Tokens Support...")
    
    required_tokens = [
        "<|start|>", "<|end|>", "<|message|>", "<|channel|>", 
        "<|constrain|>", "<|return|>", "<|call|>"
    ]
    
    # Verify tokens are defined
    special_token_values = [token.value for token in SpecialToken]
    
    for token in required_tokens:
        assert token in special_token_values, f"Token {token} not found in SpecialToken enum"
    
    print("✓ All required special tokens are supported")

def test_message_structure():
    """Test basic message format parsing."""
    print("Testing Message Structure...")
    
    parser = HarmonyParser()
    test_message = "<|start|>role:user<|message|>Hello world!<|end|>"
    
    messages = parser.parse_conversation(test_message)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    
    message = messages[0]
    assert message.role == Role.USER, f"Expected USER role, got {message.role}"
    assert message.content == "Hello world!", f"Expected 'Hello world!', got '{message.content}'"
    
    print("✓ Basic message structure parsing works correctly")

def test_all_roles():
    """Test support for all required roles."""
    print("Testing Role Support...")
    
    parser = HarmonyParser()
    required_roles = ["system", "developer", "user", "assistant", "tool"]
    
    for role_name in required_roles:
        test_message = f"<|start|>role:{role_name}<|message|>Test content<|end|>"
        messages = parser.parse_conversation(test_message)
        
        assert len(messages) == 1, f"Failed to parse {role_name} role"
        assert messages[0].role.value == role_name, f"Role mismatch for {role_name}"
    
    print("✓ All required roles (system, developer, user, assistant, tool) are supported")

def test_assistant_channels():
    """Test assistant message channels."""
    print("Testing Assistant Channels...")
    
    parser = HarmonyParser()
    required_channels = ["final", "analysis", "commentary"]
    
    for channel_name in required_channels:
        test_message = f"<|start|>role:assistant,channel:{channel_name}<|message|>Test content<|end|>"
        messages = parser.parse_conversation(test_message)
        
        assert len(messages) == 1, f"Failed to parse {channel_name} channel"
        assert messages[0].channel.value == channel_name, f"Channel mismatch for {channel_name}"
    
    print("✓ All required channels (final, analysis, commentary) are supported")

def test_tool_calls():
    """Test function calling with recipients and constraints."""
    print("Testing Tool Calls...")
    
    parser = HarmonyParser()
    
    # Test basic tool call
    tool_message = '''<|start|>role:assistant<|message|>Testing tool call.
<|call|>weather<|{"location": "Tokyo"}|><|end|>'''
    
    messages = parser.parse_conversation(tool_message)
    assert len(messages) == 1, "Expected 1 message"
    assert len(messages[0].tool_calls) == 1, "Expected 1 tool call"
    
    tool_call = messages[0].tool_calls[0]
    assert tool_call["name"] == "weather", f"Expected 'weather', got {tool_call['name']}"
    assert tool_call["parameters"]["location"] == "Tokyo", "Tool parameters not parsed correctly"
    
    print("✓ Tool calls with parameters are parsed correctly")

def test_reasoning_separation():
    """Test separation of reasoning from final output."""
    print("Testing Reasoning Output Separation...")
    
    parser = HarmonyParser()
    harmony_text = create_harmony_example()
    messages = parser.parse_conversation(harmony_text)
    
    # Test reasoning extraction
    reasoning_messages = parser.extract_reasoning(messages)
    user_facing_messages = parser.extract_user_facing(messages)
    
    assert len(reasoning_messages) > 0, "No reasoning messages found"
    assert len(user_facing_messages) > 0, "No user-facing messages found"
    
    # Verify reasoning messages are analysis channel
    for msg in reasoning_messages:
        assert msg.is_reasoning(), "Reasoning message check failed"
        assert msg.channel == Channel.ANALYSIS, "Expected analysis channel for reasoning"
    
    # Verify user-facing messages are final channel or no channel
    for msg in user_facing_messages:
        if msg.role == Role.ASSISTANT:
            assert msg.channel in [Channel.FINAL, None], "User-facing message has wrong channel"
    
    print("✓ Reasoning output separation works correctly")

def test_builtin_tools():
    """Test built-in tools support (browser and python)."""
    print("Testing Built-in Tools Support...")
    
    parser = HarmonyParser()
    
    # Test browser tool
    browser_text = create_browser_tool_example()
    browser_messages = parser.parse_conversation(browser_text)
    browser_tools = parser.extract_tool_calls(browser_messages)
    
    browser_tool_found = any(tool["tool_name"] == "browser" for tool in browser_tools)
    assert browser_tool_found, "Browser tool not found in parsed tool calls"
    
    # Test python tool
    python_text = create_python_tool_example()
    python_messages = parser.parse_conversation(python_text)
    python_tools = parser.extract_tool_calls(python_messages)
    
    python_tool_found = any(tool["tool_name"] == "python" for tool in python_tools)
    assert python_tool_found, "Python tool not found in parsed tool calls"
    
    print("✓ Built-in tools (browser and python) are supported")

def test_parser_capabilities():
    """Test all parser capabilities mentioned in requirements."""
    print("Testing Parser Capabilities...")
    
    parser = HarmonyParser()
    harmony_text = create_harmony_example()
    messages = parser.parse_conversation(harmony_text)
    
    # 1. Extract individual messages
    assert len(messages) > 0, "Cannot extract individual messages"
    
    # 2. Identify message roles, channels, recipients, and content types
    for message in messages:
        assert hasattr(message, 'role'), "Message missing role"
        assert hasattr(message, 'channel'), "Message missing channel attribute"
        assert hasattr(message, 'recipient'), "Message missing recipient attribute"
        assert hasattr(message, 'content'), "Message missing content"
    
    # 3. Handle multi-message responses with proper separation
    user_facing = parser.extract_user_facing(messages)
    reasoning = parser.extract_reasoning(messages)
    assert len(user_facing) > 0 or len(reasoning) > 0, "Cannot separate message types"
    
    # 4. Parse tool calls and their parameters
    tool_calls = parser.extract_tool_calls(messages)
    if tool_calls:
        for tool_call in tool_calls:
            assert "tool_name" in tool_call, "Tool call missing name"
            assert "parameters" in tool_call, "Tool call missing parameters"
    
    # 5. Distinguish between user-facing and internal reasoning
    if reasoning:
        reasoning_msg = reasoning[0]
        assert reasoning_msg.is_reasoning(), "Cannot identify reasoning messages"
    
    if user_facing:
        user_msg = user_facing[0]
        if user_msg.role == Role.ASSISTANT:
            assert user_msg.is_user_facing(), "Cannot identify user-facing messages"
    
    print("✓ All parser capabilities are working correctly")

def test_constraint_parsing():
    """Test constraint parsing functionality."""
    print("Testing Constraint Parsing...")
    
    parser = HarmonyParser()
    constrained_text = create_constrained_example()
    messages = parser.parse_conversation(constrained_text)
    
    # Find message with constraints
    constrained_message = None
    for message in messages:
        if message.constraints:
            constrained_message = message
            break
    
    assert constrained_message is not None, "No message with constraints found"
    assert len(constrained_message.constraints) > 0, "Constraints not parsed"
    assert "Respond only with facts, no opinions" in constrained_message.constraints[0], "Constraint content incorrect"
    
    print("✓ Constraint parsing works correctly")

def test_display_formatting():
    """Test display formatting functionality."""
    print("Testing Display Formatting...")
    
    parser = HarmonyParser()
    harmony_text = create_harmony_example()
    messages = parser.parse_conversation(harmony_text)
    
    # Test formatting without reasoning
    display_without = parser.format_for_display(messages, include_reasoning=False)
    assert len(display_without) > 0, "Display formatting failed"
    assert "analysis" not in display_without.lower(), "Reasoning included when it shouldn't be"
    
    # Test formatting with reasoning
    display_with = parser.format_for_display(messages, include_reasoning=True)
    assert len(display_with) > 0, "Display formatting with reasoning failed"
    assert len(display_with) >= len(display_without), "Reasoning version should be longer or equal"
    
    print("✓ Display formatting works correctly")

def test_error_handling():
    """Test robust error handling."""
    print("Testing Error Handling...")
    
    parser = HarmonyParser()
    
    # Test empty input
    messages = parser.parse_conversation("")
    assert len(messages) == 0, "Empty input should return no messages"
    
    # Test invalid input
    messages = parser.parse_conversation("This is not harmony format")
    assert len(messages) == 0, "Invalid input should return no messages"
    
    # Test malformed harmony
    messages = parser.parse_conversation("<|start|>invalid<|message|>test<|end|>")
    assert len(messages) == 0, "Malformed harmony should return no messages"
    
    print("✓ Error handling is robust")

def main():
    """Run comprehensive validation of harmony parser."""
    print("COMPREHENSIVE HARMONY PARSER VALIDATION")
    print("=" * 60)
    print()
    
    tests = [
        test_special_tokens,
        test_message_structure,
        test_all_roles,
        test_assistant_channels,
        test_tool_calls,
        test_reasoning_separation,
        test_builtin_tools,
        test_parser_capabilities,
        test_constraint_parsing,
        test_display_formatting,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("\n" + "=" * 60)
    print(f"VALIDATION COMPLETE: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL REQUIREMENTS SUCCESSFULLY IMPLEMENTED!")
        print("\nThe harmony parser implementation meets all requirements:")
        print("✓ Special tokens parsing")
        print("✓ Message structure handling") 
        print("✓ All roles support")
        print("✓ Channel parsing")
        print("✓ Tool calls with parameters")
        print("✓ Reasoning output separation")
        print("✓ Built-in tools support")
        print("✓ Comprehensive parser capabilities")
        print("✓ Constraint handling")
        print("✓ Display formatting")
        print("✓ Robust error handling")
        print("=" * 60)
        return 0
    else:
        print(f"❌ {total - passed} requirements not fully met")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())