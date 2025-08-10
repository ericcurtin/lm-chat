#!/usr/bin/env python3
"""
Example usage of the Harmony Parser for OpenAI's gpt-oss models.

This script demonstrates various scenarios and use cases for parsing
harmony-formatted responses.
"""

from harmony_parser import (
    HarmonyParser, 
    create_harmony_example,
    create_browser_tool_example,
    create_python_tool_example,
    create_constrained_example
)


def demo_basic_parsing():
    """Demonstrate basic harmony message parsing."""
    print("=" * 60)
    print("BASIC HARMONY PARSING DEMO")
    print("=" * 60)
    
    parser = HarmonyParser()
    harmony_text = create_harmony_example()
    
    print("Raw harmony text:")
    print("-" * 40)
    print(harmony_text)
    print()
    
    # Parse the conversation
    messages = parser.parse_conversation(harmony_text)
    
    print(f"Parsed {len(messages)} messages:")
    print("-" * 40)
    
    for i, message in enumerate(messages, 1):
        print(f"{i}. Role: {message.role.value}")
        if message.channel:
            print(f"   Channel: {message.channel.value}")
        if message.recipient:
            print(f"   Recipient: {message.recipient}")
        print(f"   Content: {message.content}")
        if message.tool_calls:
            print(f"   Tool Calls: {len(message.tool_calls)}")
            for tool_call in message.tool_calls:
                print(f"     - {tool_call['name']}: {tool_call['parameters']}")
        if message.constraints:
            print(f"   Constraints: {message.constraints}")
        print()


def demo_reasoning_separation():
    """Demonstrate separation of reasoning from final output."""
    print("=" * 60)
    print("REASONING SEPARATION DEMO")
    print("=" * 60)
    
    parser = HarmonyParser()
    harmony_text = create_harmony_example()
    messages = parser.parse_conversation(harmony_text)
    
    # Extract reasoning messages
    reasoning_messages = parser.extract_reasoning(messages)
    user_facing_messages = parser.extract_user_facing(messages)
    
    print("REASONING (Analysis Channel):")
    print("-" * 40)
    for message in reasoning_messages:
        print(f"{message.role.value}: {message.content}")
    print()
    
    print("USER-FACING CONTENT:")
    print("-" * 40)
    for message in user_facing_messages:
        role_display = message.role.value
        if message.channel:
            role_display += f" ({message.channel.value})"
        print(f"{role_display}: {message.content}")
        if message.tool_calls:
            for tool_call in message.tool_calls:
                print(f"  [Tool: {tool_call['name']}]")
    print()


def demo_tool_call_extraction():
    """Demonstrate tool call extraction and parsing."""
    print("=" * 60)
    print("TOOL CALL EXTRACTION DEMO")
    print("=" * 60)
    
    parser = HarmonyParser()
    
    # Test with browser tool example
    print("Browser Tool Example:")
    print("-" * 30)
    browser_text = create_browser_tool_example()
    browser_messages = parser.parse_conversation(browser_text)
    browser_tools = parser.extract_tool_calls(browser_messages)
    
    for tool in browser_tools:
        print(f"Tool: {tool['tool_name']}")
        print(f"From: {tool['message_role']} ({tool['message_channel']})")
        print(f"Parameters: {tool['parameters']}")
        print()
    
    # Test with python tool example
    print("Python Tool Example:")
    print("-" * 30)
    python_text = create_python_tool_example()
    python_messages = parser.parse_conversation(python_text)
    python_tools = parser.extract_tool_calls(python_messages)
    
    for tool in python_tools:
        print(f"Tool: {tool['tool_name']}")
        print(f"From: {tool['message_role']} ({tool['message_channel']})")
        print(f"Parameters: {tool['parameters']}")
        print()


def demo_constraint_handling():
    """Demonstrate constraint parsing."""
    print("=" * 60)
    print("CONSTRAINT HANDLING DEMO")
    print("=" * 60)
    
    parser = HarmonyParser()
    constrained_text = create_constrained_example()
    
    print("Raw constrained conversation:")
    print("-" * 40)
    print(constrained_text)
    print()
    
    messages = parser.parse_conversation(constrained_text)
    
    print("Parsed messages with constraints:")
    print("-" * 40)
    for message in messages:
        print(f"Role: {message.role.value}")
        if message.constraints:
            print(f"Constraints: {message.constraints}")
        print(f"Content: {message.content}")
        print()


def demo_format_for_display():
    """Demonstrate formatting messages for display."""
    print("=" * 60)
    print("DISPLAY FORMATTING DEMO")
    print("=" * 60)
    
    parser = HarmonyParser()
    harmony_text = create_harmony_example()
    messages = parser.parse_conversation(harmony_text)
    
    print("WITHOUT REASONING:")
    print("-" * 30)
    display_text = parser.format_for_display(messages, include_reasoning=False)
    print(display_text)
    print()
    
    print("WITH REASONING:")
    print("-" * 30)
    display_text_with_reasoning = parser.format_for_display(messages, include_reasoning=True)
    print(display_text_with_reasoning)
    print()


def demo_complex_conversation():
    """Demonstrate parsing a complex multi-turn conversation."""
    print("=" * 60)
    print("COMPLEX CONVERSATION DEMO")
    print("=" * 60)
    
    complex_conversation = '''<|start|>role:system<|message|>You are a helpful AI assistant with access to tools.<|end|>

<|start|>role:user<|message|>I need to analyze some data and then send an email with the results.<|end|>

<|start|>role:assistant,channel:analysis<|message|>The user wants to analyze data and send an email. This is a multi-step task that will require:
1. Understanding what data needs analysis
2. Performing the analysis (likely with Python)
3. Formatting results for email
4. Sending the email

I should ask for clarification on the data first.<|end|>

<|start|>role:assistant,channel:final<|message|>I can help you analyze data and send an email with the results. Could you please provide more details about:

1. What type of data you need analyzed?
2. What kind of analysis you're looking for?
3. Who should receive the email?<|end|>

<|start|>role:user<|message|>I have a CSV file with sales data. I need to calculate monthly totals and send a summary to my manager at manager@company.com<|end|>

<|start|>role:assistant,channel:analysis<|message|>Now I have the details:
- CSV file with sales data
- Need monthly totals
- Send to manager@company.com

I'll need to:
1. Use Python to read and analyze the CSV
2. Calculate monthly totals
3. Format the results
4. Send email (though I should note I can't actually send emails, just show how it would be done)<|end|>

<|start|>role:assistant,channel:final<|message|>I'll help you analyze the sales data and prepare an email summary. Let me start by analyzing your CSV file.

<|call|>python<|{"code": "import pandas as pd\nimport datetime\n\n# Note: In a real scenario, you'd provide the actual CSV file\n# For demo purposes, I'll create sample data\ndata = {\n    'date': ['2024-01-15', '2024-01-28', '2024-02-10', '2024-02-25', '2024-03-05'],\n    'sales': [1200, 1500, 1800, 2100, 1350]\n}\ndf = pd.DataFrame(data)\ndf['date'] = pd.to_datetime(df['date'])\ndf['month'] = df['date'].dt.to_period('M')\n\nmonthly_totals = df.groupby('month')['sales'].sum()\nprint('Monthly Sales Totals:')\nprint(monthly_totals)\nprint(f'\\nTotal Sales: ${monthly_totals.sum():,}')"}|><|end|>

<|start|>role:tool<|message|>Monthly Sales Totals:
2024-01    2700
2024-02    3900
2024-03    1350
Freq: M, Name: sales, dtype: int64

Total Sales: $7,950<|end|>

<|start|>role:assistant,channel:commentary<|message|>The analysis shows good growth from January to February, with March being a partial month. This is useful information for the manager.<|end|>

<|start|>role:assistant,channel:final<|message|>Perfect! Here's your sales analysis summary:

**Monthly Sales Totals:**
- January 2024: $2,700
- February 2024: $3,900  
- March 2024: $1,350

**Total Sales: $7,950**

Now I'll help you format this for an email to your manager:

<|call|>email_composer<|{"to": "manager@company.com", "subject": "Monthly Sales Analysis Summary", "body": "Dear Manager,\\n\\nPlease find below the monthly sales analysis:\\n\\nJanuary 2024: $2,700\\nFebruary 2024: $3,900\\nMarch 2024: $1,350 (partial month)\\n\\nTotal Sales: $7,950\\n\\nKey insights:\\n- 44% growth from January to February\\n- Strong performance trend\\n\\nBest regards"}|><|end|>

The email has been formatted and is ready to send. Note that I cannot actually send emails, but you can copy this content to your email client.<|end|>'''
    
    parser = HarmonyParser()
    messages = parser.parse_conversation(complex_conversation)
    
    print(f"Parsed {len(messages)} messages from complex conversation")
    print()
    
    print("CONVERSATION SUMMARY:")
    print("-" * 30)
    display_text = parser.format_for_display(messages, include_reasoning=False)
    print(display_text)
    print()
    
    print("EXTRACTED TOOL CALLS:")
    print("-" * 30)
    tool_calls = parser.extract_tool_calls(messages)
    for i, tool in enumerate(tool_calls, 1):
        print(f"{i}. {tool['tool_name']} (from {tool['message_role']})")
        print(f"   Parameters: {tool['parameters']}")
        print()
    
    print("REASONING CHAIN:")
    print("-" * 30)
    reasoning = parser.extract_reasoning(messages)
    for message in reasoning:
        print(f"Analysis: {message.content}")
        print()


def main():
    """Run all demonstration functions."""
    print("HARMONY PARSER DEMONSTRATION")
    print("=" * 60)
    print()
    
    demo_basic_parsing()
    print("\n" + "="*60 + "\n")
    
    demo_reasoning_separation()
    print("\n" + "="*60 + "\n")
    
    demo_tool_call_extraction()
    print("\n" + "="*60 + "\n")
    
    demo_constraint_handling()
    print("\n" + "="*60 + "\n")
    
    demo_format_for_display()
    print("\n" + "="*60 + "\n")
    
    demo_complex_conversation()
    
    print("\nDemonstration complete!")


if __name__ == "__main__":
    main()