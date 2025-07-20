#!/usr/bin/env python3
"""Example script to test relevance evaluation."""

import asyncio
from datetime import datetime, timedelta

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.evaluation import (
    CompositeRelevanceEvaluator,
    HeuristicRelevanceEvaluator,
)
from memory_agent.core.interfaces import MessageRole


async def create_sample_conversation():
    """Create a sample conversation with varying relevance."""
    blocks = []
    
    # Block 1: Initial greeting (moderate relevance)
    blocks.append(ConversationBlock(
        block_id="block-1",
        messages=[
            Message(role=MessageRole.USER, content="Hello! I need help with Python programming."),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=30),
    ))
    
    # Block 2: Good response (high relevance)
    blocks.append(ConversationBlock(
        block_id="block-2",
        messages=[
            Message(role=MessageRole.ASSISTANT, content="Hello! I'd be happy to help you with Python programming. What specific topic or problem are you working on?"),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=29),
    ))
    
    # Block 3: Specific question (high relevance)
    blocks.append(ConversationBlock(
        block_id="block-3",
        messages=[
            Message(role=MessageRole.USER, content="I'm trying to understand decorators. Can you explain how they work with a simple example?"),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=28),
    ))
    
    # Block 4: Detailed answer (high relevance)
    blocks.append(ConversationBlock(
        block_id="block-4",
        messages=[
            Message(role=MessageRole.ASSISTANT, content="""Decorators in Python are a way to modify or enhance functions without changing their code. Here's a simple example:

```python
def timer_decorator(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

@timer_decorator
def slow_function():
    time.sleep(1)
    return "Done!"

# When you call slow_function(), it will print the execution time
result = slow_function()  # Prints: "slow_function took 1.00 seconds"
```

The `@timer_decorator` syntax is syntactic sugar for `slow_function = timer_decorator(slow_function)`."""),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=27),
    ))
    
    # Block 5: Off-topic comment (low relevance)
    blocks.append(ConversationBlock(
        block_id="block-5",
        messages=[
            Message(role=MessageRole.USER, content="By the way, what's the weather like today?"),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=25),
    ))
    
    # Block 6: Acknowledgment but redirect (moderate relevance)
    blocks.append(ConversationBlock(
        block_id="block-6",
        messages=[
            Message(role=MessageRole.ASSISTANT, content="I'm focused on helping with Python programming. Let's continue with decorators - do you have any questions about the example?"),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=24),
    ))
    
    # Block 7: Back on topic (high relevance)
    blocks.append(ConversationBlock(
        block_id="block-7",
        messages=[
            Message(role=MessageRole.USER, content="Yes, can decorators take arguments themselves?"),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=23),
    ))
    
    # Block 8: Filler response (low relevance)
    blocks.append(ConversationBlock(
        block_id="block-8",
        messages=[
            Message(role=MessageRole.ASSISTANT, content="Yes, they can."),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=22),
    ))
    
    # Block 9: Better response (high relevance)
    blocks.append(ConversationBlock(
        block_id="block-9",
        messages=[
            Message(role=MessageRole.ASSISTANT, content="""Actually, let me provide a better explanation. Decorators can indeed take arguments. Here's how:

```python
def repeat(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(times=3)
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")  # Prints "Hello, Alice!" three times
```

The pattern is: decorator factory → decorator → wrapper function."""),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=21),
    ))
    
    # Block 10: Error/confusion (low relevance)
    blocks.append(ConversationBlock(
        block_id="block-10",
        messages=[
            Message(role=MessageRole.USER, content="Wait, I think there was an error above. Never mind."),
        ],
        created_at=datetime.utcnow() - timedelta(minutes=15),
    ))
    
    return blocks


async def test_heuristic_evaluation():
    """Test heuristic relevance evaluation."""
    print("\n=== Testing Heuristic Evaluation ===\n")
    
    evaluator = HeuristicRelevanceEvaluator()
    blocks = await create_sample_conversation()
    
    for i, block in enumerate(blocks):
        # Use surrounding blocks as context
        context = blocks[max(0, i-3):i] + blocks[i+1:min(len(blocks), i+4)]
        
        score = await evaluator.evaluate(block, context)
        
        print(f"Block {block.block_id}:")
        print(f"  Content: {block.messages[0].content[:60]}...")
        print(f"  Overall Score: {score.overall_score:.2f}")
        print(f"  Decision: {score.decision.value}")
        print(f"  Factors:")
        print(f"    - Semantic: {score.factors.semantic_alignment:.2f}")
        print(f"    - Temporal: {score.factors.temporal_relevance:.2f}")
        print(f"    - Goal: {score.factors.goal_contribution:.2f}")
        print(f"    - Quality: {score.factors.information_quality:.2f}")
        print(f"    - Factual: {score.factors.factual_consistency:.2f}")
        print(f"  Explanation: {score.explanation}")
        print()


async def test_composite_evaluation():
    """Test composite relevance evaluation."""
    print("\n=== Testing Composite Evaluation ===\n")
    
    # Use composite evaluator (heuristic only for this demo)
    evaluator = CompositeRelevanceEvaluator(use_llm=False)
    blocks = await create_sample_conversation()
    
    # Evaluate entire conversation
    results = []
    for i, block in enumerate(blocks):
        context = blocks[max(0, i-3):i] + blocks[i+1:min(len(blocks), i+4)]
        score = await evaluator.evaluate(block, context)
        results.append((block, score))
    
    # Show summary
    print("Conversation Summary:")
    print("-" * 60)
    
    keep_count = sum(1 for _, s in results if s.decision.value == "keep")
    review_count = sum(1 for _, s in results if s.decision.value == "review")
    remove_count = sum(1 for _, s in results if s.decision.value == "remove")
    
    print(f"Total blocks: {len(blocks)}")
    print(f"Keep: {keep_count}")
    print(f"Review: {review_count}")
    print(f"Remove: {remove_count}")
    print()
    
    # Show blocks marked for removal
    print("Blocks marked for removal:")
    for block, score in results:
        if score.decision.value == "remove":
            print(f"  - {block.block_id}: {block.messages[0].content[:60]}...")
            print(f"    Reason: {score.explanation}")
    
    # Show average scores
    avg_score = sum(s.overall_score for _, s in results) / len(results)
    print(f"\nAverage relevance score: {avg_score:.2f}")


async def main():
    """Run all tests."""
    await test_heuristic_evaluation()
    await test_composite_evaluation()


if __name__ == "__main__":
    print("Testing Relevance Evaluation System")
    print("===================================")
    asyncio.run(main())