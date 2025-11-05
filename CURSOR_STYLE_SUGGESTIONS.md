# Cursor-Style AI Suggestions for Legal Contracts

## Architecture: Ghost Text with Multi-User Awareness

### 1. Data Model

```python
# Backend: AI Suggestion (per-user, private)
class CursorStyleSuggestion:
    id: int
    user_id: int  # WHO sees this (private to them)
    document_id: int
    agent_type: str  # "risk", "compliance", "style"

    # Position in document
    anchor_position: int  # Where to insert ghost text
    anchor_text: str  # Text before cursor (for validation)

    # Suggestion content
    alternatives: List[str]  # ["option 1", "option 2", "option 3"]
    current_index: int  # Which alternative is shown (0-indexed)

    # Metadata
    explanation: str  # "Unlimited liability is risky"
    source: str  # "Based on TechCorp NDA v2.1"
    confidence: float

    # Lifecycle
    status: str  # "active", "accepted", "rejected", "expired"
    created_at: datetime
    expires_at: datetime  # Auto-expire if doc changes too much


# Frontend: Ghost Text State (React/Vue)
interface GhostTextState {
  suggestionId: number;
  position: number;  // Character offset in editor
  alternatives: string[];
  currentIndex: number;
  isVisible: boolean;

  // Styling
  ghostTextColor: string;  // "rgba(128,128,128,0.5)"
  cursorOffset: number;  // Where user's cursor is relative to ghost
}
```

### 2. Frontend Implementation (Quill.js / ProseMirror / Slate.js)

#### Option A: Using Quill.js (Easiest for Rich Text)

```typescript
// quill-ghost-text-module.ts
import Quill from 'quill';

class GhostTextBlot extends Quill.import('blots/inline') {
  static blotName = 'ghostText';
  static tagName = 'span';
  static className = 'ghost-text';

  static create(value) {
    let node = super.create(value);
    node.setAttribute('contenteditable', 'false');
    node.setAttribute('data-suggestion-id', value.suggestionId);
    node.innerText = value.text;
    node.style.color = 'rgba(128, 128, 128, 0.5)';
    node.style.fontStyle = 'italic';
    return node;
  }
}

Quill.register(GhostTextBlot);

// Usage in collaborative editor
class CollaborativeEditor {
  quill: Quill;
  currentSuggestion: CursorStyleSuggestion | null = null;

  async onTextChange(delta, source) {
    if (source === 'user') {
      // User is typing - request AI suggestion
      const cursorPosition = this.quill.getSelection()?.index || 0;
      const textBeforeCursor = this.quill.getText(0, cursorPosition);

      // Debounced AI request
      this.requestSuggestion(textBeforeCursor, cursorPosition);
    }
  }

  async requestSuggestion(context: string, position: number) {
    // WebSocket to backend
    this.ws.send({
      type: 'request_suggestion',
      context: context,
      position: position,
      trigger: 'typing'  // or 'manual'
    });
  }

  onSuggestionReceived(suggestion: CursorStyleSuggestion) {
    this.currentSuggestion = suggestion;

    // Insert ghost text at cursor
    const cursorPos = this.quill.getSelection()?.index || 0;

    this.quill.formatText(cursorPos, suggestion.alternatives[0].length, {
      ghostText: {
        suggestionId: suggestion.id,
        text: suggestion.alternatives[0]
      }
    });

    // Show hint UI
    this.showSuggestionHint(suggestion);
  }

  showSuggestionHint(suggestion: CursorStyleSuggestion) {
    // Floating hint near cursor
    const hint = document.createElement('div');
    hint.className = 'suggestion-hint';
    hint.innerHTML = `
      <span class="key">⇥ Tab</span> to accept
      ${suggestion.alternatives.length > 1 ?
        `<span class="key">→</span> Next (${suggestion.current_index + 1}/${suggestion.alternatives.length})`
        : ''}
      <span class="key">Esc</span> to dismiss
    `;

    // Position near cursor
    const cursorBounds = this.quill.getBounds(this.quill.getSelection()?.index || 0);
    hint.style.top = `${cursorBounds.bottom + 5}px`;
    hint.style.left = `${cursorBounds.left}px`;

    document.body.appendChild(hint);
  }

  setupKeyboardHandlers() {
    this.quill.keyboard.addBinding({
      key: 'Tab',
      handler: () => {
        if (this.currentSuggestion) {
          this.acceptSuggestion();
          return false; // Prevent default Tab behavior
        }
      }
    });

    this.quill.keyboard.addBinding({
      key: 'Escape',
      handler: () => {
        if (this.currentSuggestion) {
          this.rejectSuggestion();
          return false;
        }
      }
    });

    this.quill.keyboard.addBinding({
      key: 'ArrowRight',
      handler: () => {
        if (this.currentSuggestion && this.currentSuggestion.alternatives.length > 1) {
          this.cycleNextSuggestion();
          return false;
        }
      }
    });
  }

  acceptSuggestion() {
    if (!this.currentSuggestion) return;

    const ghostText = this.currentSuggestion.alternatives[this.currentSuggestion.current_index];
    const cursorPos = this.quill.getSelection()?.index || 0;

    // Remove ghost text formatting
    this.removeGhostText();

    // Insert real text
    this.quill.insertText(cursorPos, ghostText, 'user');

    // Send to backend (store feedback + broadcast to others)
    this.ws.send({
      type: 'accept_suggestion',
      suggestion_id: this.currentSuggestion.id,
      applied_text: ghostText,
      position: cursorPos
    });

    // Clear state
    this.currentSuggestion = null;
  }

  rejectSuggestion() {
    if (!this.currentSuggestion) return;

    this.removeGhostText();

    // Send feedback to backend (for memory)
    this.ws.send({
      type: 'reject_suggestion',
      suggestion_id: this.currentSuggestion.id,
      reason: 'manual_dismiss'
    });

    this.currentSuggestion = null;
  }

  cycleNextSuggestion() {
    if (!this.currentSuggestion) return;

    const nextIndex = (this.currentSuggestion.current_index + 1) % this.currentSuggestion.alternatives.length;
    this.currentSuggestion.current_index = nextIndex;

    // Update ghost text display
    this.removeGhostText();
    this.onSuggestionReceived(this.currentSuggestion);
  }

  removeGhostText() {
    const ghostBlots = document.querySelectorAll('.ghost-text');
    ghostBlots.forEach(blot => blot.remove());

    const hints = document.querySelectorAll('.suggestion-hint');
    hints.forEach(hint => hint.remove());
  }

  // Handle remote edits from other users
  onRemoteEdit(edit: RemoteEdit) {
    if (this.currentSuggestion) {
      // Check if edit conflicts with ghost text position
      const editStart = edit.position;
      const editEnd = edit.position + edit.length;
      const ghostStart = this.currentSuggestion.anchor_position;

      if (editStart <= ghostStart && editEnd >= ghostStart) {
        // Conflict - expire suggestion
        this.removeGhostText();
        this.currentSuggestion = null;
      }
    }

    // Apply remote edit to editor
    this.quill.updateContents(edit.delta, 'api');
  }
}
```

#### CSS Styling

```css
/* Ghost text styling */
.ghost-text {
  color: rgba(128, 128, 128, 0.5) !important;
  font-style: italic;
  pointer-events: none;
  user-select: none;
}

/* Multi-user: different colors for different agents */
.ghost-text[data-agent="risk"] {
  color: rgba(255, 100, 100, 0.5) !important; /* Red tint for risk */
}

.ghost-text[data-agent="compliance"] {
  color: rgba(100, 100, 255, 0.5) !important; /* Blue tint for compliance */
}

.ghost-text[data-agent="style"] {
  color: rgba(100, 255, 100, 0.5) !important; /* Green tint for style */
}

/* Suggestion hint (floating keyboard shortcuts) */
.suggestion-hint {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 1000;
  animation: fadeIn 0.2s;
}

.suggestion-hint .key {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  margin: 0 4px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Alternative suggestions counter */
.suggestion-hint .counter {
  color: rgba(255, 255, 255, 0.7);
  margin-left: 8px;
}
```

### 3. Backend: AI Suggestion Generation

```python
# agents/cursor_style_agent.py
from typing import List, Optional
import asyncio

class CursorStyleSuggestionEngine:
    def __init__(self, memory_service, agent_registry):
        self.memory = memory_service
        self.agents = agent_registry

    async def generate_suggestions(
        self,
        user_id: int,
        document_id: int,
        context: str,  # Text before cursor
        position: int,
        trigger: str = "typing"
    ) -> Optional[CursorStyleSuggestion]:
        """
        Generate Cursor-style inline suggestions based on context.
        """

        # 1. Detect what user is trying to write
        intent = await self.detect_intent(context)

        # 2. Query memory for similar patterns
        past_patterns = await self.memory.query_user_patterns(
            user_id=user_id,
            intent=intent,
            limit=5
        )

        # 3. Run relevant agents in parallel
        agent_tasks = []
        if intent == "liability_clause":
            agent_tasks.append(self.agents.risk.suggest_liability_text(context))
        elif intent == "termination_clause":
            agent_tasks.append(self.agents.compliance.suggest_termination(context))

        agent_results = await asyncio.gather(*agent_tasks)

        # 4. Generate multiple alternatives
        alternatives = []

        # From agents
        for result in agent_results:
            if result and result.confidence > 0.7:
                alternatives.append(result.suggested_text)

        # From memory (what user accepted before)
        for pattern in past_patterns:
            if pattern.acceptance_rate > 0.8:
                alternatives.append(pattern.text)

        # Deduplicate and rank
        alternatives = self.rank_alternatives(alternatives, context)

        if not alternatives:
            return None

        # 5. Create suggestion
        suggestion = CursorStyleSuggestion(
            user_id=user_id,
            document_id=document_id,
            agent_type=intent,
            anchor_position=position,
            anchor_text=context[-50:],  # Last 50 chars for validation
            alternatives=alternatives[:3],  # Max 3 alternatives
            current_index=0,
            explanation=agent_results[0].explanation if agent_results else "",
            source=agent_results[0].source if agent_results else "",
            confidence=agent_results[0].confidence if agent_results else 0.8,
            status="active",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=5)
        )

        return suggestion

    async def detect_intent(self, context: str) -> str:
        """
        Detect what type of clause user is writing.
        """
        context_lower = context.lower()

        if "liable" in context_lower or "indemnif" in context_lower:
            return "liability_clause"
        elif "terminate" in context_lower or "cancel" in context_lower:
            return "termination_clause"
        elif "confidential" in context_lower:
            return "confidentiality_clause"
        elif "payment" in context_lower or "fee" in context_lower:
            return "payment_clause"
        else:
            return "general"

    def rank_alternatives(self, alternatives: List[str], context: str) -> List[str]:
        """
        Rank alternatives by relevance and diversity.
        """
        # Simple deduplication
        unique = list(dict.fromkeys(alternatives))

        # TODO: Use embedding similarity to ensure diversity
        # For now, just return first 3
        return unique[:3]


# WebSocket handler
@websocket("/ws/suggestions/{doc_id}")
async def suggestion_stream(websocket: WebSocket, doc_id: int, token: str):
    user = authenticate(token)
    suggestion_engine = CursorStyleSuggestionEngine(memory_service, agent_registry)

    await websocket.accept()

    try:
        async for message in websocket.iter_json():
            if message["type"] == "request_suggestion":
                # Generate suggestion
                suggestion = await suggestion_engine.generate_suggestions(
                    user_id=user.id,
                    document_id=doc_id,
                    context=message["context"],
                    position=message["position"],
                    trigger=message.get("trigger", "typing")
                )

                if suggestion:
                    # Send to this user only (private)
                    await websocket.send_json({
                        "type": "suggestion",
                        "suggestion": suggestion.dict()
                    })

            elif message["type"] == "accept_suggestion":
                # Store feedback
                await memory_service.store_feedback(
                    user_id=user.id,
                    suggestion_id=message["suggestion_id"],
                    action="accepted",
                    applied_text=message["applied_text"]
                )

                # Broadcast to other users as regular edit
                await broadcast_to_room(doc_id, {
                    "type": "remote_edit",
                    "user_id": user.id,
                    "position": message["position"],
                    "text": message["applied_text"],
                    "source": "ai_suggestion"
                }, exclude=user.id)

            elif message["type"] == "reject_suggestion":
                # Store negative feedback (important for learning!)
                await memory_service.store_feedback(
                    user_id=user.id,
                    suggestion_id=message["suggestion_id"],
                    action="rejected",
                    reason=message.get("reason", "manual_dismiss")
                )

    except WebSocketDisconnect:
        pass
```

### 4. Multi-User Conflict Handling

**Critical Question:** What happens when User A has ghost text, and User B edits that area?

**Solution: Position Tracking with Auto-Expiration**

```python
class SuggestionConflictResolver:
    def check_suggestion_validity(
        self,
        suggestion: CursorStyleSuggestion,
        remote_edit: RemoteEdit
    ) -> bool:
        """
        Check if a remote edit invalidates an active suggestion.
        """
        edit_start = remote_edit.position
        edit_end = remote_edit.position + len(remote_edit.text)
        ghost_pos = suggestion.anchor_position

        # If remote edit overlaps with ghost position, expire suggestion
        if edit_start <= ghost_pos <= edit_end:
            return False  # Invalid

        # If remote edit changes anchor text, expire suggestion
        if remote_edit.position < ghost_pos:
            # Anchor text may have shifted
            # Validate by checking if anchor_text still exists
            current_text = get_document_text(suggestion.document_id)
            anchor_exists = current_text[ghost_pos-50:ghost_pos] == suggestion.anchor_text[-50:]
            return anchor_exists

        return True  # Still valid

# In WebSocket handler
async def on_remote_edit(user_id: int, doc_id: int, remote_edit: RemoteEdit):
    # Get all active suggestions for this document
    active_suggestions = await db.query(
        CursorStyleSuggestion
    ).filter(
        document_id=doc_id,
        status="active"
    ).all()

    # Check each suggestion for conflicts
    for suggestion in active_suggestions:
        if not conflict_resolver.check_suggestion_validity(suggestion, remote_edit):
            # Expire suggestion
            suggestion.status = "expired"
            await db.commit()

            # Notify user that their suggestion is stale
            await send_to_user(suggestion.user_id, {
                "type": "suggestion_expired",
                "suggestion_id": suggestion.id,
                "reason": "document_changed"
            })
```

### 5. Advanced: Partial Acceptance (Like GitHub Copilot)

**Feature:** Accept first few words, see more suggestions

```typescript
setupKeyboardHandlers() {
  // Accept word-by-word with Ctrl+→
  this.quill.keyboard.addBinding({
    key: 'ArrowRight',
    ctrlKey: true,
    handler: () => {
      if (this.currentSuggestion) {
        this.acceptPartialSuggestion();
        return false;
      }
    }
  });
}

acceptPartialSuggestion() {
  if (!this.currentSuggestion) return;

  const ghostText = this.currentSuggestion.alternatives[this.currentSuggestion.current_index];
  const words = ghostText.split(' ');

  if (words.length === 0) return;

  // Accept first word
  const firstWord = words[0] + ' ';
  const cursorPos = this.quill.getSelection()?.index || 0;

  this.quill.insertText(cursorPos, firstWord, 'user');

  // Update suggestion with remaining text
  this.currentSuggestion.alternatives[this.currentSuggestion.current_index] = words.slice(1).join(' ');
  this.currentSuggestion.anchor_position += firstWord.length;

  // Re-render ghost text
  this.removeGhostText();
  this.onSuggestionReceived(this.currentSuggestion);
}
```

---

## 6. Demo Flow: Cursor-Style in Action

### Scenario: Junior Associate writing liability clause

```
T=0s: User types "The Provider shall be "
      ↓
      AI detects: liability clause intent
      ↓
      AI queries memory: User rejected unlimited liability before
      ↓
      AI generates 3 alternatives

T=2s: Ghost text appears
      "The Provider shall be liable only for direct damages up to contract value"
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                (gray italic text)

      [⇥ Tab · → Next (1/3) · Esc]

T=5s: User presses → to see alternatives
      Alternative 2/3: "liable only for actual damages not exceeding fees paid"
      Alternative 3/3: "liable for proven damages with reasonable limits"

T=7s: User presses Tab to accept alternative 1
      ↓
      Text becomes real (black, not gray)
      ↓
      Broadcast to other users: "User A added text (AI-assisted)"
      ↓
      Store in memory: User accepted "limited liability" suggestion
```

---

## 7. Why This is Better Than Tooltips

| Feature | Tooltip/Badge | Cursor-Style |
|---------|---------------|--------------|
| **Visual intrusion** | High (popup blocks text) | Low (inline gray text) |
| **Accept speed** | 2 clicks | 1 keystroke (Tab) |
| **Multiple alternatives** | Dropdown menu | Cycle with arrows |
| **Typing interruption** | Yes (must dismiss popup) | No (keeps typing = auto-dismiss) |
| **Familiarity** | Custom UI | Copilot/Gmail pattern |
| **Mobile support** | Better (tap to see) | Harder (no Tab key) |

**Recommendation:** Use Cursor-style for desktop, fall back to tooltips on mobile.

---

## 8. Integration with Your Existing Agents

```python
# Your existing agents (risk, compliance, etc.)
# Just need to return text alternatives instead of just explanations

class RiskAgent:
    async def suggest_text(self, context: str) -> SuggestionResult:
        """
        NEW: Return actual text to insert, not just analysis.
        """
        clause_type = self.detect_clause_type(context)

        if clause_type == "liability":
            # Generate 3 alternatives
            alternatives = [
                "liable only for direct damages up to the contract value",
                "liable for actual damages not exceeding the fees paid under this agreement",
                "liable for proven damages, capped at reasonable limits"
            ]

            return SuggestionResult(
                alternatives=alternatives,
                explanation="Unlimited liability is high risk. These options provide protection.",
                source="Based on your TechCorp NDA (rejected unlimited liability)",
                confidence=0.92
            )
```

---

## Ready to implement?

I can help you:
1. **Set up Quill.js with ghost text** (or choose different editor)
2. **Create WebSocket handler for suggestions**
3. **Integrate with your existing agents**
4. **Add keyboard shortcuts**
5. **Handle multi-user conflicts**

Which part should we start with?
