"""
Inline AI suggestions service for patent writing.
Provides contextual, real-time writing assistance.

MVP VERSION (v2.1):
- Simple 20-word context for fast completions
- Memory service integrated (ready for enhancements)
- 1634 legal documents available for queries
- Fast and cost-effective

"""

import openai
import os
import uuid
from typing import Dict, Any
from app.services.memory_service import get_memory_service
from app.services.learning_service import get_learning_service


class InlineSuggestionsService:
    """Service for generating contextual inline suggestions during patent writing."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Allow model override via environment variable
        self.model = os.getenv("INLINE_SUGGESTIONS_MODEL", "gpt-3.5-turbo")

        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

        # Memory service for context retrieval
        self.memory = get_memory_service()
        
        # Learning service for personalization and feedback
        self.learning = get_learning_service()

        print(f"🤖 InlineSuggestionsService initialized with model: {self.model}")
        print(f"📚 Learning service integrated for personalization")

    async def generate_suggestion(
        self,
        content: str,
        cursor_pos: int,
        context_before: str,
        context_after: str,
        suggestion_type: str = "completion",
        client_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate inline suggestion with legal knowledge grounding.

        ENHANCED APPROACH:
        - Uses last 20 words for context
        - Queries 3-tier memory hierarchy (Legal → Firm → Client)
        - Provides legally-grounded suggestions with visual badges
        """

        if not self.client:
            return {
                "suggested_text": "",
                "reasoning": "API key not configured",
                "confidence": 0.0
            }

        try:
            # Use only last 20 words before cursor
            words_before = context_before.split()[-20:]
            simple_context = " ".join(words_before)

            # Generate unique suggestion ID for tracking
            suggestion_id = f"sugg_{uuid.uuid4().hex[:12]}"
            
            # 🚀 ENHANCEMENT: Query 4-tier memory hierarchy + learned patterns
            context_parts = []
            last_50_chars = context_before[-50:].lower()

            has_legal = False
            has_firm = False
            has_client = False
            has_learned_patterns = False

            try:
                # Level 1: Legal knowledge (only when legal terms detected)
                if any(term in last_50_chars for term in ['section', 'act', 'patent', 'claim', 'algorithm', 'software']):
                    legal_refs = self.memory.query_legal_knowledge(
                        query=context_before[-100:],
                        limit=1
                    )
                    if legal_refs:
                        context_parts.append(f"LEGAL: {legal_refs[0].get('memory', '')[:150]}")
                        has_legal = True
                        print(f"⚖️ Using legal knowledge")

                # Level 2: Firm knowledge (ALWAYS query for writing style!)
                firm_refs = self.memory.query_firm_knowledge(
                    query=context_before[-100:],
                    limit=2  # Get top 2 examples
                )
                if firm_refs:
                    firm_examples = []
                    for ref in firm_refs[:2]:
                        firm_examples.append(ref.get('memory', '')[:100])
                    
                    combined_firm = " | ".join(firm_examples)
                    context_parts.append(f"FIRM WRITING STYLE: {combined_firm}")
                    has_firm = True
                    
                    # Show which documents are being used
                    docs_used = [ref.get('metadata', {}).get('title', 'N/A') for ref in firm_refs]
                    print(f"💼 Using firm knowledge from: {', '.join(docs_used)}")

                # Level 3: Client/episodic memory (personalization)
                if client_id:
                    client_refs = self.memory.query_client_memory(
                        client_id=client_id,
                        query=context_before[-100:],
                        limit=1
                    )
                    if client_refs:
                        context_parts.append(f"YOUR HISTORY: {client_refs[0].get('memory', '')[:150]}")
                        has_client = True
                        print(f"📋 Using client history for {client_id}")
                    
                    # Level 4: Learned patterns (NEW!)
                    learned_patterns = await self.learning.get_client_patterns(
                        client_id=client_id,
                        pattern_type="phrases"
                    )
                    if learned_patterns:
                        # Extract top phrases
                        top_phrases = []
                        for pattern in learned_patterns[:3]:
                            phrases = pattern.get('metadata', {}).get('phrases', [])
                            if phrases:
                                top_phrases.extend(phrases[:2])
                        
                        if top_phrases:
                            context_parts.append(f"YOUR COMMON PHRASES: {', '.join(top_phrases[:5])}")
                            has_learned_patterns = True
                            print(f"🧠 Using learned patterns for {client_id}")

            except Exception as e:
                print(f"⚠️ Could not query memory: {e}")

            legal_context = "\n\n" + "\n".join(context_parts) if context_parts else ""

            # Enhanced prompt with legal grounding
            system_prompt = f"You are an expert patent writing assistant with knowledge of Indian Patent Law. Complete the text naturally (5-10 words) following patent drafting conventions.{legal_context}"
            user_prompt = f"Complete this text:\n\n{simple_context}"

            response = self.client.chat.completions.create(
                model=self.model,  # GPT-3.5-turbo by default
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": user_prompt
                }],
                max_tokens=20,
                temperature=0.3
            )

            suggested_text = response.choices[0].message.content.strip()

            # Basic validation: not too long, no markdown
            word_count = len(suggested_text.split())
            if word_count > 20:
                # Trim to first 15 words if too long
                suggested_text = ' '.join(suggested_text.split()[:15])
                print(f"⚠️ Trimmed suggestion from {word_count} to 15 words")
            
            # Remove markdown if present
            if suggested_text.startswith('#'):
                suggested_text = suggested_text.lstrip('#').strip()

            # Only return if we have actual text
            if not suggested_text or len(suggested_text) < 2:
                return {
                    "suggested_text": "",
                    "reasoning": "AI returned empty or invalid suggestion",
                    "confidence": 0.0
                }

            print(f"✅ Generated suggestion: '{suggested_text}' ({len(suggested_text.split())} words)")

            # Calculate confidence based on grounding tiers (including learned patterns)
            tier_count = sum([has_legal, has_firm, has_client, has_learned_patterns])

            if tier_count == 4:
                confidence = 0.98  # All 4 tiers = highest confidence
                grounding = " + Legal + Firm + Your History + Learned Patterns"
            elif tier_count == 3:
                confidence = 0.95  # 3 tiers
                if has_legal and has_firm and has_client:
                    grounding = " + Legal + Firm + Your History"
                elif has_legal and has_firm and has_learned_patterns:
                    grounding = " + Legal + Firm + Learned Patterns"
                else:
                    grounding = " + Multiple Sources"
            elif tier_count == 2:
                confidence = 0.90  # 2 tiers
                if has_legal and has_firm:
                    grounding = " + Legal + Firm Knowledge"
                elif has_legal and has_client:
                    grounding = " + Legal + Your History"
                else:
                    grounding = " + Firm + Your History"
            elif has_legal:
                confidence = 0.85  # Just legal
                grounding = " + Legal Knowledge"
            elif has_firm:
                confidence = 0.80  # Just firm
                grounding = " + Firm Knowledge"
            elif has_client:
                confidence = 0.80  # Just client
                grounding = " + Your History"
            else:
                confidence = 0.75  # No grounding
                grounding = ""

            return {
                "suggestion_id": suggestion_id,
                "suggested_text": suggested_text,
                "reasoning": f"AI completion using {self.model}{grounding}",
                "confidence": confidence,
                "model_used": self.model,
                "legal_grounded": has_legal,
                "firm_grounded": has_firm,
                "client_grounded": has_client,
                "learned_patterns": has_learned_patterns,
                "context_before": context_before[-100:],  # For feedback tracking
                "context_after": context_after[:100]
            }

        except Exception as e:
            print(f"❌ OpenAI API error in inline suggestions: {e}")
            return {
                "suggested_text": "",
                "reasoning": "AI service temporarily unavailable",
                "confidence": 0.0
            }
