"""Basic usage example of the memory agent entities."""

import asyncio
from datetime import datetime

from memory_agent.core.entities import ConversationBlock, Message, MessageChain
from memory_agent.core.interfaces import (
    Decision,
    MessageRole,
    MessageType,
    StorageTier,
)


async def demonstrate_message_chain():
    """Demonstrate basic message chain operations."""
    print("=== Message Chain Demo ===\n")
    
    # Create a message chain
    chain = MessageChain()
    session_id = "demo-session-001"
    
    # Add user message
    user_msg = Message(
        role=MessageRole.USER,
        content="What's the weather in Paris?",
        type=MessageType.TEXT,
    )
    await chain.add_message(user_msg, session_id)
    print(f"Added user message: {user_msg}")
    
    # Add agent planning message
    agent_plan = Message(
        role=MessageRole.ASSISTANT,
        content="I'll check the weather in Paris for you.",
        type=MessageType.TEXT,
    )
    await chain.add_message(agent_plan, session_id)
    print(f"Added agent message: {agent_plan}")
    
    # Add tool call message
    tool_call = Message(
        role=MessageRole.ASSISTANT,
        content="",
        type=MessageType.TOOL_CALL,
        tool_name="web_search",
        tool_parameters={"query": "current weather Paris France"},
    )
    await chain.add_message(tool_call, session_id)
    print(f"Added tool call: web_search")
    
    # Add tool result
    tool_result = Message(
        role=MessageRole.TOOL,
        content="Paris, France: 22°C, Partly cloudy",
        type=MessageType.TOOL_RESULT,
        tool_name="web_search",
        tool_call_id=tool_call.id,
    )
    await chain.add_message(tool_result, session_id)
    print(f"Added tool result: {tool_result.content}")
    
    # Get all messages
    messages = await chain.get_messages(session_id)
    print(f"\nTotal messages in chain: {len(messages)}")
    
    # Demonstrate chain summary
    summary = chain.get_chain_summary(session_id)
    print(f"Chain summary: {summary}")
    
    return chain, session_id


def demonstrate_conversation_blocks(messages):
    """Demonstrate conversation block creation and evaluation."""
    print("\n\n=== Conversation Blocks Demo ===\n")
    
    blocks = []
    
    # Create blocks for each message
    for i, msg in enumerate(messages):
        block = ConversationBlock(
            sequence_number=i + 1,
            session_id="demo-session-001",
            content=msg.content,
            source=msg.role.value,
            message_id=msg.id,
            tool_name=msg.tool_name,
        )
        
        # Simulate relevance scoring
        if msg.role == MessageRole.USER:
            block.relevance_score = 1.0  # User queries always relevant
        elif msg.type == MessageType.TOOL_RESULT:
            block.relevance_score = 0.95  # Tool results highly relevant
        elif msg.type == MessageType.TOOL_CALL:
            block.relevance_score = 0.85  # Tool calls relevant
        else:
            block.relevance_score = 0.90  # Agent responses relevant
        
        blocks.append(block)
        print(f"Created block: {block.to_summary()}")
    
    # Demonstrate retention scoring
    print("\nRetention scores:")
    for block in blocks:
        score = block.calculate_retention_score()
        print(f"  Block {block.sequence_number}: {score:.2f}")
    
    # Simulate aging and tier migration
    print("\nChecking tier migration needs:")
    blocks[0].timestamp = datetime.utcnow().replace(
        hour=datetime.utcnow().hour - 7
    )  # Make first block 7 hours old
    
    if blocks[0].should_compress():
        print(f"  Block {blocks[0].sequence_number} should be compressed")
        blocks[0].memory_tier = StorageTier.WARM
    
    return blocks


def demonstrate_self_correction():
    """Demonstrate self-correction scenario."""
    print("\n\n=== Self-Correction Demo ===\n")
    
    # Create a scenario with an error
    messages = [
        Message(
            role=MessageRole.USER,
            content="What's the capital of France?",
            type=MessageType.TEXT,
        ),
        Message(
            role=MessageRole.ASSISTANT,
            content="I'll find the capital of France for you.",
            type=MessageType.TEXT,
        ),
        Message(
            role=MessageRole.ASSISTANT,
            content="",
            type=MessageType.TOOL_CALL,
            tool_name="web_search",
            tool_parameters={"query": "capital of Germany"},  # Wrong query!
        ),
        Message(
            role=MessageRole.TOOL,
            content="Berlin is the capital of Germany",
            type=MessageType.TOOL_RESULT,
            tool_name="web_search",
        ),
    ]
    
    # Simulate evaluation detecting the error
    print("Evaluating message relevance...")
    for i, msg in enumerate(messages):
        if i == 3:  # Tool result about Germany
            print(f"  Message {i+1}: IRRELEVANT - Wrong country information")
            print("  Decision: DISCARD this message")
            
            # Create correction
            correction = Message(
                role=MessageRole.ASSISTANT,
                content="",
                type=MessageType.CORRECTION,
                tool_name="web_search",
                tool_parameters={"query": "capital of France"},
                parent_message_id=messages[2].id,
                correction_reason="Incorrect country in search query",
            )
            print(f"\n  Creating correction: {correction.tool_parameters}")
    
    print("\nSelf-correction complete!")


async def main():
    """Run all demonstrations."""
    # Message chain demo
    chain, session_id = await demonstrate_message_chain()
    messages = await chain.get_messages(session_id)
    
    # Conversation blocks demo
    blocks = demonstrate_conversation_blocks(messages)
    
    # Self-correction demo
    demonstrate_self_correction()
    
    print("\n✅ All demos completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())