#!/usr/bin/env python3
"""Test script to verify self-correction behavior."""

import asyncio
import json
import time
from datetime import datetime

import httpx


async def test_self_correction():
    """Test the self-correction behavior of the memory agent."""
    base_url = "http://localhost:8000/api/v1"
    
    # Create a session
    async with httpx.AsyncClient() as client:
        print("1. Creating test session...")
        session_resp = await client.post(f"{base_url}/sessions/", json={})
        session = session_resp.json()
        session_id = session["session_id"]
        print(f"   Session created: {session_id}")
        
        # Send a series of messages designed to trigger self-correction
        messages = [
            # Good, relevant message
            "What is the capital of France?",
            
            # Irrelevant messages that should be corrected
            "asdfghjkl random gibberish",
            "1234567890 just numbers",
            "The weather is nice today",  # Off-topic
            
            # Back to relevant
            "Can you tell me more about Paris?",
            
            # More irrelevant content
            "Lorem ipsum dolor sit amet",
            "Testing testing 123",
            
            # Relevant question
            "What are the main attractions in Paris?",
        ]
        
        print("\n2. Sending messages to trigger self-correction...")
        for i, message in enumerate(messages):
            print(f"\n   Message {i+1}: {message[:50]}...")
            
            # Send message
            chat_resp = await client.post(
                f"{base_url}/agent/chat",
                json={
                    "session_id": session_id,
                    "message": message
                }
            )
            
            response = chat_resp.json()
            print(f"   Response: {response['response'][:100]}...")
            print(f"   Corrections made so far: {response.get('corrections_made', 0)}")
            
            # Small delay between messages
            await asyncio.sleep(1)
        
        # Wait a bit for background self-correction to run
        print("\n3. Waiting 10 seconds for self-correction cycle...")
        await asyncio.sleep(10)
        
        # Check memory stats
        print("\n4. Checking memory statistics...")
        stats_resp = await client.get(f"{base_url}/memory/stats")
        memory_stats = stats_resp.json()
        print(f"   Total blocks: {memory_stats['total_blocks']}")
        print(f"   Tier breakdown: {json.dumps(memory_stats['tier_breakdown'], indent=2)}")
        
        # Get agent stats
        agent_stats_resp = await client.get(f"{base_url}/agent/stats")
        agent_stats = agent_stats_resp.json()
        print(f"\n5. Agent statistics:")
        print(f"   Total messages: {agent_stats['total_messages']}")
        print(f"   Total corrections: {agent_stats['total_corrections']}")
        print(f"   Average relevance score: {agent_stats['avg_relevance_score']}")
        
        # List memory blocks to see what was kept/removed
        print("\n6. Checking individual memory blocks...")
        blocks_resp = await client.get(
            f"{base_url}/memory/blocks",
            params={"session_id": session_id, "limit": 20}
        )
        blocks = blocks_resp.json()
        
        print(f"   Remaining blocks: {len(blocks)}")
        for block in blocks:
            print(f"   - Block {block['block_id']}")
            print(f"     Content: {block['content'][:50]}...")
            print(f"     Relevance: {block['relevance_score']:.2f}")
            print(f"     Tier: {block['memory_tier']}")
            print()
        
        # Force a correction cycle
        print("\n7. Forcing immediate correction cycle...")
        # Note: This endpoint might not exist, but we can try
        try:
            force_resp = await client.post(f"{base_url}/agent/force-correction/{session_id}")
            if force_resp.status_code == 200:
                corrections = force_resp.json()
                print(f"   Forced corrections: {len(corrections)}")
                for corr in corrections:
                    print(f"   - {corr['type']}: {corr.get('reason', 'No reason given')}")
        except:
            print("   (Force correction endpoint not available)")
        
        print("\n8. Final memory state check...")
        final_blocks_resp = await client.get(
            f"{base_url}/memory/blocks",
            params={"session_id": session_id, "limit": 20}
        )
        final_blocks = final_blocks_resp.json()
        
        print(f"   Final block count: {len(final_blocks)}")
        print("\n   Summary of remaining content:")
        for block in final_blocks:
            relevance = block['relevance_score']
            status = "✓" if relevance > 0.6 else "✗"
            print(f"   {status} {block['content'][:60]}... (relevance: {relevance:.2f})")


if __name__ == "__main__":
    print("Memory Agent Self-Correction Test")
    print("=" * 50)
    asyncio.run(test_self_correction())