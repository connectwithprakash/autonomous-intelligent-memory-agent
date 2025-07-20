# Self-Correction Behavior Test Guide

## How to Test Self-Correction in the Dashboard

### Step 1: Open the Dashboard
Navigate to http://localhost:5173 and go to the Chat tab.

### Step 2: Send Test Messages
Send these messages in order to trigger self-correction:

1. **Good Message**: "What is machine learning?"
   - This should get a high relevance score

2. **Gibberish**: "asdfghjkl qwerty"
   - This should get a very low relevance score and be marked for removal

3. **Off-topic**: "The weather is nice today"
   - This is coherent but off-topic, should get low relevance

4. **Good Message**: "Can you explain neural networks?"
   - Back to relevant content

5. **Spam**: "test test test 123 123"
   - Low quality, should be removed

6. **Good Message**: "How does backpropagation work?"
   - Relevant technical question

### Step 3: Check Memory Tab
After sending these messages:
1. Go to the **Memory** tab
2. Look at the memory blocks
3. You should see:
   - Blocks with high relevance scores (> 0.6) are kept
   - Blocks with low relevance scores (< 0.4) should be marked for removal
   - The tier distribution chart shows how messages are categorized

### Step 4: Wait for Self-Correction
The self-correction loop runs every 60 seconds. You can:
1. Wait 1-2 minutes
2. Check the Memory tab again
3. Low-relevance messages should be removed or improved

### Step 5: Check Statistics Tab
Go to the **Statistics** tab to see:
- Total corrections made
- Average relevance score
- Real-time updates as corrections happen

## What to Look For

### Signs of Self-Correction Working:
1. **Automatic Removal**: Gibberish and spam messages disappear from memory
2. **Relevance Scores**: Each block shows its relevance score
3. **Correction Count**: Statistics show increasing correction count
4. **Memory Tiers**: Relevant messages stay in HOT tier, others move to WARM/COLD

### Dashboard Indicators:
- **Memory Tab**: Shows remaining blocks after correction
- **Statistics Tab**: Shows total corrections and average relevance
- **Real-time Updates**: WebSocket updates show corrections as they happen

## Expected Behavior

1. **High Relevance (> 0.6)**: Technical questions about ML/AI - KEPT
2. **Medium Relevance (0.4-0.6)**: Somewhat related content - REVIEWED
3. **Low Relevance (< 0.4)**: Gibberish, spam, off-topic - REMOVED

The agent should maintain only relevant, high-quality conversation history!