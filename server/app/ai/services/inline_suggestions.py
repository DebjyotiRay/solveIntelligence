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

            # 🚀 ENHANCEMENT: Check if user is writing about legal concepts
            legal_context = ""
            last_50_chars = context_before[-50:].lower()

            # Detect legal references
            if any(term in last_50_chars for term in ['section', 'act', 'patent', 'claim', 'algorithm', 'software']):
                try:
                    # Query legal memory for context
                    legal_refs = self.memory.query_legal_knowledge(
                        query=context_before[-100:],  # Last 100 chars for context
                        limit=2
                    )

                    if legal_refs:
                        # Add legal knowledge to prompt
                        legal_context = f"\n\nRELEVANT LEGAL CONTEXT:\n{legal_refs[0].get('memory', '')[:200]}"
                        print(f"💡 Found legal context: {legal_refs[0].get('metadata', {}).get('section', 'N/A')}")
                except Exception as e:
                    print(f"⚠️ Could not query legal memory: {e}")

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

            # Higher confidence if legal grounding was used
            confidence = 0.85 if legal_context else 0.75

            return {
                "suggested_text": suggested_text,
                "reasoning": f"AI completion using {self.model}" + (" + Legal Memory" if legal_context else ""),
                "confidence": confidence,
                "model_used": self.model,
                "legal_grounded": bool(legal_context)
            }

        except Exception as e:
            print(f"❌ OpenAI API error in inline suggestions: {e}")
            return {
                "suggested_text": "",
                "reasoning": "AI service temporarily unavailable",
                "confidence": 0.0
            }
