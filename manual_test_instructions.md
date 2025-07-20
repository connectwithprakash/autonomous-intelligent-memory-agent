# Manual Testing Instructions for Self-Correction

## Quick Test in Dashboard

### 1. Send These Messages in Chat:
Send these messages one by one in the Chat tab:

```
1. "Hello"
2. "asdfghjkl"  
3. "What is Python?"
4. "random random random"
5. "Tell me about machine learning"
```

### 2. Check Memory Tab Immediately:
- Go to Memory tab
- You should see all 10 blocks (5 user messages + 5 assistant responses)
- Note the relevance scores - gibberish should have low scores

### 3. Wait 60-90 seconds:
The self-correction runs every 60 seconds in the background.

### 4. Refresh Memory Tab:
- Low relevance messages (gibberish) should be removed
- You should see fewer blocks
- Only relevant messages remain

## What's Happening Behind the Scenes:

1. **Relevance Evaluation**: Each message gets scored on:
   - Semantic alignment (30%)
   - Temporal relevance (20%) 
   - Goal contribution (25%)
   - Information quality (15%)
   - Factual consistency (10%)

2. **Self-Correction Actions**:
   - Score < 0.7: Message is reviewed
   - Score < 0.4: Message could be removed (but threshold is set to 0.7)
   - Currently, with threshold at 0.7, most low-quality messages will be corrected

3. **Background Process**:
   - Runs every 60 seconds
   - Analyzes last 10 messages
   - Removes or improves problematic content

## Check the Console:
In the terminal running the API server, you should see logs like:
```
[info] Found problematic blocks session_id=xxx count=2
[info] Removed irrelevant block block_id=xxx score=0.3
[info] Applied corrections session_id=xxx correction_count=2
```

## Note on Current Configuration:
The system is using a threshold of 0.7, which means it's quite aggressive about corrections. Messages need a relevance score above 0.7 to be kept without review.