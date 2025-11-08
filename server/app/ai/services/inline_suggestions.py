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
from typing import Dict, Any
from app.services.memory_service import get_memory_service


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

        # Memory service available for future enhancements
        self.memory = get_memory_service()

        print(f"🤖 InlineSuggestionsService initialized with model: {self.model}")

    async def generate_suggestion(
        self,
        content: str,
        cursor_pos: int,
        context_before: str,
        context_after: str,
        suggestion_type: str = "completion"
    ) -> Dict[str, Any]:
        """
        Generate inline suggestion with legal knowledge grounding.

        ENHANCED APPROACH:
        - Uses last 20 words for context
        - Queries legal memory for relevant law
        - Provides legally-grounded suggestions
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

            # 🚀 ENHANCEMENT: Query 3-tier memory hierarchy
            context_parts = []
            last_50_chars = context_before[-50:].lower()

            # Detect legal/patent references
            if any(term in last_50_chars for term in ['section', 'act', 'patent', 'claim', 'algorithm', 'software']):
                try:
                    # Level 1: Legal knowledge
                    legal_refs = self.memory.query_legal_knowledge(
                        query=context_before[-100:],
                        limit=1
                    )
                    if legal_refs:
                        context_parts.append(f"LEGAL: {legal_refs[0].get('memory', '')[:150]}")

                    # Level 2: Firm knowledge (always query for writing style)
                    firm_refs = self.memory.query_firm_knowledge(
                        query=context_before[-100:],
                        limit=1
                    )
                    if firm_refs:
                        context_parts.append(f"FIRM STYLE: {firm_refs[0].get('memory', '')[:150]}")
                        print(f"💼 Using firm knowledge: {firm_refs[0].get('metadata', {}).get('title', 'N/A')}")

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

            # Higher confidence if grounded in knowledge
            has_legal = "LEGAL:" in legal_context
            has_firm = "FIRM STYLE:" in legal_context

            if has_legal and has_firm:
                confidence = 0.90  # Both legal + firm = highest confidence
                grounding = " + Legal + Firm Knowledge"
            elif has_legal:
                confidence = 0.85  # Just legal
                grounding = " + Legal Knowledge"
            elif has_firm:
                confidence = 0.80  # Just firm
                grounding = " + Firm Knowledge"
            else:
                confidence = 0.75  # No grounding
                grounding = ""

            return {
                "suggested_text": suggested_text,
                "reasoning": f"AI completion using {self.model}{grounding}",
                "confidence": confidence,
                "model_used": self.model,
                "legal_grounded": has_legal,
                "firm_grounded": has_firm
            }

        except Exception as e:
            print(f"❌ OpenAI API error in inline suggestions: {e}")
            return {
                "suggested_text": "",
                "reasoning": "AI service temporarily unavailable",
                "confidence": 0.0
            }
