"""
Inline AI suggestions service for patent writing.
Provides contextual, real-time writing assistance.

SIMPLIFIED VERSION (v2.0):
- Uses GPT-3.5-turbo (20x cheaper than GPT-4: $0.0005 vs $0.01 per 1K tokens)
- Simple 20-word context (no document-wide memory)
- Fast and cost-effective for as-you-type completions
- Reduced from 428 lines to ~80 lines

"""

import openai
import os
from typing import Dict, Any


class InlineSuggestionsService:
    """Service for generating contextual inline suggestions during patent writing."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Allow model override via environment variable
        self.model = os.getenv("INLINE_SUGGESTIONS_MODEL", "gpt-4.1")

        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None


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
        Generate inline suggestion using simple 20-word context.

        SIMPLIFIED APPROACH:
        - Uses only last 20 words before cursor (no full document analysis)
        - Single AI call with focused prompt
        - Basic validation (length, format)
        """

        if not self.client:
            return {
                "suggested_text": "",
                "reasoning": "API key not configured",
                "confidence": 0.0
            }

        try:
            # SIMPLIFIED: Use only last 20 words before cursor
            words_before = context_before.split()[-20:]  # Last 20 words
            simple_context = " ".join(words_before)

            # Simple, focused prompt
            system_prompt = "You are a patent writing assistant. Complete the text with 5 natural words that fit the context."
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
            if len(suggested_text.split()) > 10 or suggested_text.startswith('#'):
                return {
                    "suggested_text": "",
                    "reasoning": "Suggestion too long or invalid format",
                    "confidence": 0.0
                }

            return {
                "suggested_text": suggested_text,
                "reasoning": f"AI completion using {self.model}",
                "confidence": 0.80,
                "model_used": self.model
            }

        except Exception as e:
            print(f"❌ OpenAI API error in inline suggestions: {e}")
            return {
                "suggested_text": "",
                "reasoning": "AI service temporarily unavailable",
                "confidence": 0.0
            }
