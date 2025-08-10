#!/usr/bin/env python3
"""
Test script for harmony parser integration with lm-chat.py
"""

import sys
import os

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harmony_parser import HarmonyParser, create_harmony_example

def test_basic_functionality():
    """Test basic harmony parser functionality."""
    print("Testing Harmony Parser Basic Functionality")
    print("=" * 50)
    
    parser = HarmonyParser()
    
    # Test with example harmony text
    harmony_text = create_harmony_example()
    messages = parser.parse_conversation(harmony_text)
    
    print(f"✓ Parsed {len(messages)} messages")
    
    # Test message extraction
    user_facing = parser.extract_user_facing(messages)
    reasoning = parser.extract_reasoning(messages)
    tool_calls = parser.extract_tool_calls(messages)
    
    print(f"✓ Found {len(user_facing)} user-facing messages")
    print(f"✓ Found {len(reasoning)} reasoning messages")
    print(f"✓ Found {len(tool_calls)} tool calls")
    
    # Test display formatting
    display_text = parser.format_for_display(messages, include_reasoning=True)
    print(f"✓ Generated display text ({len(display_text)} characters)")
    
    print("\nBasic functionality test passed! ✓")

def test_complex_scenarios():
    """Test complex parsing scenarios."""
    print("\nTesting Complex Scenarios")
    print("=" * 50)
    
    parser = HarmonyParser()
    
    # Test message with multiple tool calls
    complex_text = '''<|start|>role:assistant,channel:final<|message|>I'll help you with multiple tasks.

<|call|>weather<|{"location": "Tokyo"}|>
<|call|>calculator<|{"operation": "add", "a": 5, "b": 3}|>

Let me process these for you.<|end|>'''
    
    messages = parser.parse_conversation(complex_text)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    
    message = messages[0]
    assert len(message.tool_calls) == 2, f"Expected 2 tool calls, got {len(message.tool_calls)}"
    assert message.tool_calls[0]['name'] == 'weather'
    assert message.tool_calls[1]['name'] == 'calculator'
    
    print("✓ Multiple tool calls parsed correctly")
    
    # Test message with constraints
    constrained_text = '''<|start|>role:system<|message|><|constrain|>Be concise<|return|><|constrain|>Use only facts<|return|>You are a helpful assistant.<|end|>'''
    
    messages = parser.parse_conversation(constrained_text)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    
    message = messages[0]
    assert len(message.constraints) == 2, f"Expected 2 constraints, got {len(message.constraints)}"
    assert "Be concise" in message.constraints
    assert "Use only facts" in message.constraints
    
    print("✓ Multiple constraints parsed correctly")
    
    # Test malformed message (should be ignored)
    malformed_text = '''<|start|>invalid_header<|message|>This should be ignored<|end|>
<|start|>role:user<|message|>This should work<|end|>'''
    
    messages = parser.parse_conversation(malformed_text)
    assert len(messages) == 1, f"Expected 1 message (malformed ignored), got {len(messages)}"
    assert messages[0].role.value == 'user'
    
    print("✓ Malformed messages handled correctly")
    
    print("\nComplex scenarios test passed! ✓")

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\nTesting Edge Cases")
    print("=" * 50)
    
    parser = HarmonyParser()
    
    # Test empty input
    messages = parser.parse_conversation("")
    assert len(messages) == 0, f"Expected 0 messages for empty input, got {len(messages)}"
    print("✓ Empty input handled correctly")
    
    # Test input without harmony format
    regular_text = "This is just regular text without any harmony formatting."
    messages = parser.parse_conversation(regular_text)
    assert len(messages) == 0, f"Expected 0 messages for non-harmony text, got {len(messages)}"
    print("✓ Non-harmony text handled correctly")
    
    # Test incomplete message
    incomplete_text = "<|start|>role:user<|message|>Incomplete message"
    messages = parser.parse_conversation(incomplete_text)
    assert len(messages) == 0, f"Expected 0 messages for incomplete message, got {len(messages)}"
    print("✓ Incomplete messages handled correctly")
    
    # Test invalid JSON in tool call
    invalid_json_text = '''<|start|>role:assistant<|message|>Test with invalid JSON.
<|call|>tool<|{invalid json}|><|end|>'''
    
    messages = parser.parse_conversation(invalid_json_text)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    assert len(messages[0].tool_calls) == 1, f"Expected 1 tool call, got {len(messages[0].tool_calls)}"
    assert "raw" in messages[0].tool_calls[0]["parameters"], "Expected raw parameter for invalid JSON"
    print("✓ Invalid JSON in tool calls handled correctly")
    
    print("\nEdge cases test passed! ✓")

def test_import_capability():
    """Test that the module can be imported properly."""
    print("\nTesting Import Capability")
    print("=" * 50)
    
    try:
        # Try importing from lm-chat.py location
        import harmony_parser
        print("✓ harmony_parser module imported successfully")
        
        # Test main classes
        parser = harmony_parser.HarmonyParser()
        print("✓ HarmonyParser class instantiated successfully")
        
        # Test enums
        role = harmony_parser.Role.USER
        channel = harmony_parser.Channel.FINAL
        token = harmony_parser.SpecialToken.START
        print("✓ Enums accessible successfully")
        
        # Test example functions
        example = harmony_parser.create_harmony_example()
        assert len(example) > 0, "Example should not be empty"
        print("✓ Example functions working correctly")
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    
    print("\nImport capability test passed! ✓")
    return True

def main():
    """Run all tests."""
    print("HARMONY PARSER INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_import_capability()
        test_basic_functionality()
        test_complex_scenarios()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("Harmony parser is ready for use.")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())