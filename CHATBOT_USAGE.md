# Grounded Chatbot - Usage Guide

## What It Does

A memory-grounded chatbot that helps users discuss and clarify AI analysis results. When users disagree with suggestions or have questions, they can chat with the AI to understand the reasoning behind suggestions.

## How It Works

### Backend Architecture

1. **Chat Service** (`server/app/services/chat_service.py`)
   - Retrieves relevant context from all 3 memory tiers (legal, firm, client)
   - Uses retrieved sources to ground AI responses
   - Includes inline citations like [1], [2] in responses

2. **Memory Integration**
   - Legal Knowledge: Indian Patent Act, IPC, case law
   - Firm Knowledge: Past successful patents, templates
   - Client Memory: User's previous documents and analysis history

3. **API Endpoint** (`POST /chat`)
   - Accepts: user message, client_id, document_id, conversation history
   - Returns: AI response with sources and citations

### Frontend Component

**ChatPanel** (`client/src/components/ChatPanel.tsx`)
- Floating chat button (💬) in bottom-right corner
- Full-featured chat interface with:
  - Message history
  - Source citations (expandable)
  - Typing indicators
  - Auto-scroll

## Usage Examples

### Example 1: Question About Analysis
**User:** "Why did you suggest changing 'computer program' to 'computer-implemented method'?"

**AI Response:**
```
According to Indian Patent Act, Section 3(k) [1], computer programs "per se"
are not patentable. However, computer-implemented methods that solve technical
problems ARE patentable [2].

Your current claim uses "computer program" which may be rejected under Section
3(k). By rephrasing to "computer-implemented method," you emphasize the technical
solution rather than the software itself.

REFERENCES:
[1] Indian Patent Act, Section 3(k)
[2] Previous Firm Patent: Software Patents Strategy (Firm Knowledge, 2023)
```

### Example 2: Disagreement With Suggestion
**User:** "I don't think I need to add enablement details. The invention is obvious."

**AI Response:**
```
I understand your concern. However, 35 USC 112(a) requires sufficient detail for
a person skilled in the art to make and use the invention [1].

In your previous patent application [2], the examiner rejected similar claims for
lack of enablement. Adding specific implementation details (even if obvious to you)
strengthens the application and reduces rejection risk.

I recommend adding at least one detailed embodiment showing how the system works.

REFERENCES:
[1] Indian Patent Act (Legal Document)
[2] Client's Previous Application (patent, 2024-10-15)
```

### Example 3: Legal Question
**User:** "Can you explain Section 3(k) in simple terms?"

**AI Response:**
```
Section 3(k) of the Indian Patent Act [1] excludes "computer programs per se"
from patentability. In simple terms:

❌ NOT Patentable: Pure software or algorithms without technical application
✅ Patentable: Software that solves a technical problem or controls hardware

For example:
- A search algorithm alone → NOT patentable
- A medical imaging system using that algorithm → Patentable

Your current document describes an AI system for medical diagnosis [2], which
likely qualifies as a technical application and should be patentable.

REFERENCES:
[1] Indian Patent Act, Section 3(k)
[2] Current Document (Client Document)
```

## Features

### 1. Context-Aware Responses
- Retrieves 2 legal + 2 firm + 3 client sources per query
- Sources are ranked by relevance
- Only includes sources that fit in context window

### 2. Citation System
- Inline citations: [1], [2], etc.
- Expandable sources section showing:
  - Citation number
  - Full citation text
  - Source tier (legal/firm/client)

### 3. Conversation Memory
- Maintains last 6 messages for context
- Allows follow-up questions
- Understands references to previous messages

### 4. Document Context
- Automatically includes current document content
- Personalizes responses based on user's specific patent

## Testing

### Test the Backend

```bash
# Test chat endpoint directly
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Why did you suggest this change?",
    "client_id": "test_client",
    "document_id": 1,
    "document_context": "A system for AI-based medical diagnosis..."
  }'
```

### Test the Frontend

1. Start the application
2. Click the 💬 button in bottom-right
3. Ask questions like:
   - "Why did you suggest X?"
   - "Can you explain Section 3k?"
   - "I disagree with this suggestion because..."
   - "How can I make this claim stronger?"

## Configuration

### Environment Variables

```bash
# .env
OPENAI_API_KEY=your_key_here  # Required for chat
```

### Customization

**Adjust source distribution** (in `chat_service.py`):
```python
# Current: 2 legal + 2 firm + 3 client
legal_n = int(num_sources * 0.4)   # Change percentages here
firm_n = int(num_sources * 0.3)
client_n = int(num_sources * 0.3)
```

**Change model** (in `chat_service.py`):
```python
model="gpt-4o-mini"  # Fast and cheap
# or
model="gpt-4-turbo-preview"  # More capable
```

## Integration Points

### Where Users Access Chat

1. **After Analysis**: User sees suggestions, disagrees, opens chat
2. **During Writing**: User has questions about legal requirements
3. **General Help**: User needs explanation of patent concepts

### Future Enhancements

- [ ] Voice input for chat
- [ ] Export chat history
- [ ] Suggest chat questions based on analysis
- [ ] Multi-language support
- [ ] Save favorite responses
- [ ] Chat-to-edit: "Apply this suggestion to my document"

## Architecture Benefits

✅ **Simple**: One function call returns context + citations
✅ **Fast**: Uses gpt-4o-mini for quick responses
✅ **Grounded**: All responses cite actual sources from memory
✅ **Integrated**: Uses existing memory_service.py infrastructure
✅ **Scalable**: Easy to add more memory tiers or sources
