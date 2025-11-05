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
        Generate MULTIPLE inline suggestions (Cursor/Copilot style).

        ENHANCED APPROACH:
        - Uses last 30 words before cursor for better context
        - Generates 3 alternative suggestions with different styles
        - Returns alternatives array for cycling with arrow keys
        - Includes confidence and reasoning for each alternative
        """

        if not self.client:
            return {
                "alternatives": [],
                "reasoning": "API key not configured",
                "confidence": 0.0
            }

        try:
            # Use last 30 words before cursor for better context
            words_before = context_before.split()[-30:]
            simple_context = " ".join(words_before)

            # Enhanced prompt to generate 3 alternatives
            system_prompt = """You are a legal document writing assistant specializing in contracts and agreements.
Generate 3 different completions for the text, each with a different style:
1. Formal legal language (precise, traditional)
2. Clear and concise (modern, readable)
3. Detailed and protective (comprehensive, risk-averse)

Return ONLY valid JSON with an "alternatives" array of 3 strings. Example:
{"alternatives": ["formal completion", "concise completion", "detailed completion"]}"""

            user_prompt = f"Complete this legal text with 5-10 words:\n\n{simple_context}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": user_prompt
                }],
                max_tokens=150,  # More tokens for 3 alternatives
                temperature=0.5  # Slightly higher for variety
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            import json
            try:
                # Try to parse as JSON object first
                parsed = json.loads(response_text)
                if isinstance(parsed, dict):
                    # Extract array from dict
                    alternatives_raw = (
                        parsed.get("alternatives") or
                        parsed.get("suggestions") or
                        parsed.get("completions") or
                        list(parsed.values())[0] if parsed else []
                    )
                else:
                    alternatives_raw = parsed
            except json.JSONDecodeError:
                # Fallback: try to extract array from text
                import re
                array_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if array_match:
                    alternatives_raw = json.loads(array_match.group())
                else:
                    # Ultimate fallback: single suggestion
                    alternatives_raw = [response_text]

            # Validate and clean alternatives
            alternatives = []
            for alt_text in alternatives_raw[:3]:  # Max 3
                cleaned = str(alt_text).strip().strip('"').strip("'")

                # Validation: not too long, no markdown
                if len(cleaned.split()) <= 15 and not cleaned.startswith('#'):
                    alternatives.append({
                        "text": cleaned,
                        "confidence": 0.85 - (len(alternatives) * 0.05),  # Decreasing confidence
                        "reasoning": [
                            "Formal legal style",
                            "Clear and concise",
                            "Detailed and protective"
                        ][len(alternatives)] if len(alternatives) < 3 else "Alternative completion"
                    })

            # If no valid alternatives, return empty
            if not alternatives:
                return {
                    "alternatives": [],
                    "reasoning": "No valid suggestions generated",
                    "confidence": 0.0
                }

            return {
                "alternatives": alternatives,
                "reasoning": f"Generated {len(alternatives)} alternatives using {self.model}",
                "confidence": alternatives[0]["confidence"],
                "model_used": self.model
            }

        except Exception as e:
            print(f"❌ OpenAI API error in inline suggestions: {e}")
            import traceback
            traceback.print_exc()
            return {
                "alternatives": [],
                "reasoning": "AI service temporarily unavailable",
                "confidence": 0.0
            }
