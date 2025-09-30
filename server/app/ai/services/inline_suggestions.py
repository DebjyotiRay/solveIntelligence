"""
Inline AI suggestions service for patent writing.
Provides contextual, real-time writing assistance.
"""

import openai
import os
from typing import Dict, Any
from ..utils import strip_html


class InlineSuggestionsService:
    """Service for generating contextual inline suggestions during patent writing."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

        # Document memory cache for long-term context
        self._document_memory_cache = {}

    def _build_document_memory(self, content: str) -> dict:
        """Build long-term memory context from full document."""
        content_hash = hash(content)

        # Return cached analysis if available
        if content_hash in self._document_memory_cache:
            return self._document_memory_cache[content_hash]

        clean_content = strip_html(content)

        # Extract document characteristics
        memory = {
            'technical_domain': self._extract_technical_domain(clean_content),
            'writing_style': self._analyze_writing_style(clean_content),
            'key_terminology': self._extract_key_terms(clean_content),
            'document_summary': self._generate_summary(clean_content),
            'total_length': len(clean_content.split())
        }

        # Cache the analysis
        self._document_memory_cache[content_hash] = memory
        return memory

    def _extract_technical_domain(self, content: str) -> str:
        """Identify the technical domain of the patent."""
        content_lower = content.lower()

        # Patent domain keywords
        domains = {
            'wireless_communication': ['wireless', 'radio', 'antenna', 'signal', 'transmission', 'receiver'],
            'medical_device': ['medical', 'patient', 'treatment', 'therapeutic', 'clinical', 'diagnosis'],
            'optical_systems': ['optical', 'light', 'laser', 'photonic', 'fiber', 'wavelength'],
            'software_systems': ['software', 'algorithm', 'processor', 'computing', 'data', 'interface'],
            'mechanical_systems': ['mechanical', 'actuator', 'motor', 'bearing', 'mechanism', 'assembly']
        }

        domain_scores = {}
        for domain, keywords in domains.items():
            score = sum(content_lower.count(keyword) for keyword in keywords)
            domain_scores[domain] = score

        return max(domain_scores, key=domain_scores.get) if domain_scores else 'general'

    def _analyze_writing_style(self, content: str) -> str:
        """Analyze the document's writing style."""
        formal_indicators = content.count('wherein') + content.count('comprising') + content.count('disclosed')
        technical_indicators = content.count('device') + content.count('method') + content.count('system')

        if formal_indicators > technical_indicators:
            return 'formal_legal'
        else:
            return 'technical_descriptive'

    def _extract_key_terms(self, content: str) -> list:
        """Extract key technical terms from the document."""
        words = content.lower().split()

        # Common patent terms that indicate important concepts
        important_terms = []
        patent_keywords = ['device', 'system', 'method', 'apparatus', 'mechanism', 'circuit', 'module', 'component']

        for keyword in patent_keywords:
            if keyword in words:
                important_terms.append(keyword)

        return important_terms[:5]  # Return top 5 terms

    def _generate_summary(self, content: str) -> str:
        """Generate a brief summary of the document for context."""
        words = content.split()
        if len(words) < 20:
            return content

        # Extract first meaningful sentence
        sentences = content.split('.')
        for sentence in sentences[:3]:
            if len(sentence.strip()) > 20:
                return sentence.strip()[:100] + "..."

        return " ".join(words[:20]) + "..."

    def _get_immediate_context(self, before: str) -> dict:
        """Extract focused immediate context for word prediction."""
        words = before.split()

        # Focus on last 10-20 words for precise completion
        recent_words = words[-15:] if len(words) > 15 else words
        recent_text = " ".join(recent_words)

        # Analyze what type of completion is expected
        completion_type = self._predict_completion_type(recent_text)

        return {
            'recent_words': recent_words,
            'recent_text': recent_text,
            'completion_type': completion_type,
            'word_count': len(recent_words)
        }

    def _predict_completion_type(self, recent_text: str) -> str:
        """Predict what type of word completion is expected."""
        text_lower = recent_text.lower().strip()

        # Articles suggest noun phrase
        if text_lower.endswith((' a ', ' an ', ' the ')):
            return 'noun_phrase'

        # Prepositions suggest location/relationship
        if text_lower.endswith((' of ', ' for ', ' with ', ' by ', ' in ')):
            return 'noun_object'

        # Conjunctions suggest parallel structure
        if text_lower.endswith((' and ', ' or ', ' but ')):
            return 'parallel_element'

        # Patent-specific patterns
        if text_lower.endswith('comprising '):
            return 'claim_element'
        if text_lower.endswith('wherein '):
            return 'claim_limitation'

        return 'general_completion'

    def _validate_suggestion(self, suggestion: str, context: dict) -> tuple[bool, str]:
        """Validate suggestion quality and format."""
        if not suggestion or not suggestion.strip():
            return False, "Empty suggestion"

        cleaned = suggestion.strip()

        # Remove common formatting artifacts
        artifacts = ['After:', 'Before:', '...', '"', "'", '(', ')', '[', ']']
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, '')

        cleaned = cleaned.strip()

        # Validate word count (2-5 words for natural completion)
        words = cleaned.split()
        if len(words) < 2 or len(words) > 5:
            return False, f"Invalid length: {len(words)} words"

        # Check for coherence - no standalone punctuation
        if any(word in ['.', ',', ':', ';', '!', '?'] for word in words):
            return False, "Contains standalone punctuation"

        # Ensure it's appropriate completion type
        if context.get('completion_type') == 'noun_phrase':
            # Should not start with verbs
            verb_starters = ['is', 'are', 'was', 'were', 'do', 'does', 'can', 'will']
            if words[0].lower() in verb_starters:
                return False, "Inappropriate verb start for noun phrase"

        return True, cleaned

    def _analyze_context(self, content: str, before: str, after: str, section: str) -> dict:
        """Analyze context for enhanced suggestion generation."""
        return {
            'section': section,
            'sentence_position': self._get_sentence_position(before),
            'writing_pattern': self._detect_writing_pattern(before),
            'document_style': self._analyze_style(content),
            'completion_hint': self._get_completion_hint(before, section)
        }

    def _get_sentence_position(self, before: str) -> str:
        """Determine position within current sentence."""
        if before.endswith('. ') or before.endswith(': '):
            return 'sentence_start'
        elif before.count('.') == 0 and before.count(':') == 0:
            return 'sentence_beginning'
        else:
            return 'sentence_middle'

    def _detect_writing_pattern(self, before: str) -> str:
        """Detect the writing pattern for consistency."""
        if any(pattern in before.lower() for pattern in ['comprising', 'including', 'having']):
            return 'claim_enumeration'
        elif any(pattern in before.lower() for pattern in ['wherein', 'whereby', 'such that']):
            return 'claim_limitation'
        elif any(pattern in before.lower() for pattern in ['embodiment', 'implementation', 'example']):
            return 'description_detail'
        else:
            return 'general_narrative'

    def _analyze_style(self, content: str) -> str:
        """Analyze document writing style."""
        formal_indicators = content.count('wherein') + content.count('comprising') + content.count('disclosed')
        technical_indicators = content.count('device') + content.count('method') + content.count('system')
        
        if formal_indicators > technical_indicators:
            return 'formal_legal'
        else:
            return 'technical_descriptive'

    def _get_completion_hint(self, before: str, section: str) -> str:
        """Get specific completion hint based on context."""
        before_lower = before.lower()
        section_lower = section.lower()
        
        if 'claims' in section_lower:
            if before.endswith('comprising '):
                return 'claim_element'
            elif before.endswith('wherein '):
                return 'claim_limitation'
            elif before.endswith('a ') or before.endswith('an '):
                return 'claim_component'
        elif 'background' in section_lower:
            if before.endswith('prior art '):
                return 'background_reference'
            elif before.endswith('known '):
                return 'prior_knowledge'
        elif 'description' in section_lower:
            if before.endswith('embodiment '):
                return 'implementation_detail'
            elif before.endswith('example '):
                return 'example_continuation'
        
        return 'general_completion'

    def _build_rich_completion_prompt(self, document_memory: dict, immediate_context: dict) -> str:
        """Build rich contextual prompt for high-quality word completion."""
        recent_text = immediate_context['recent_text']
        completion_type = immediate_context['completion_type']
        domain = document_memory['technical_domain']
        key_terms = document_memory.get('key_terminology', [])
        doc_summary = document_memory.get('document_summary', '')
        writing_style = document_memory.get('writing_style', 'technical_descriptive')

        # Rich context with document understanding
        context_description = f"""DOCUMENT CONTEXT:
- Technical Domain: {domain.replace('_', ' ')}
- Key Technologies: {', '.join(key_terms) if key_terms else 'general patent concepts'}
- Writing Style: {writing_style.replace('_', ' ')}
- Document Summary: {doc_summary}

IMMEDIATE CONTEXT:
- Current text: "{recent_text}"
- Expected completion type: {completion_type.replace('_', ' ')}
- Word position: {"end of sentence" if recent_text.rstrip().endswith('.') else "mid-sentence"}"""

        # Specific examples based on completion type and domain
        completion_guidance = {
            'noun_phrase': f'technical noun phrases like "wireless device", "optical system", "communication module"',
            'claim_element': f'patent claim elements like "processing unit", "control circuit", "sensing apparatus"',
            'claim_limitation': f'functional descriptions like "configured to transmit", "adapted for receiving", "operable to process"',
            'noun_object': f'technical objects like "signal processing", "data transmission", "wireless communication"',
            'parallel_element': f'parallel structure elements maintaining consistency with the preceding context',
            'general_completion': f'appropriate technical terminology for {domain.replace("_", " ")} patents'
        }

        guidance = completion_guidance.get(completion_type, 'appropriate technical terminology')

        return f"""{context_description}

TASK: Complete the current text with exactly 2-4 words that:
1. Naturally continue the sentence
2. Match the document's technical domain and style
3. Follow patent writing conventions
4. Are contextually appropriate for {completion_type.replace('_', ' ')}

Expected completion style: {guidance}

Provide ONLY the completion words (2-4 words), no quotes, no explanation, no punctuation."""

    def _get_section_examples(self, section: str, hint: str) -> str:
        """Get section-specific examples for better prompting."""
        examples_map = {
            'claim_element': 'a wireless communication device, an optical sensing apparatus, a processing unit configured to',
            'claim_limitation': 'configured to transmit data, adapted to receive signals, operable to process information',
            'claim_component': 'transmitter circuit, receiver module, control processor, memory storage unit',
            'background_reference': 'discloses a method for, teaches a system that, describes an approach to',
            'prior_knowledge': 'techniques for signal processing, methods of data transmission, approaches to wireless communication',
            'implementation_detail': 'includes multiple components that, operates by coordinating between, functions through the use of',
            'example_continuation': 'demonstrates the effectiveness of, illustrates the practical application, shows the improved performance',
            'general_completion': 'technical components, operational methods, system configurations'
        }
        return examples_map.get(hint, 'appropriate technical terminology that fits the context')

    def _identify_patent_section(self, context_before: str, full_document: str) -> str:
        """Identify which section of the patent the user is currently writing in."""

        context_lower = context_before.lower()
        doc_lower = full_document.lower()

        # Check for specific patent sections based on context
        if any(keyword in context_lower for keyword in ['claim', 'claims', 'what is claimed']):
            # Determine if independent or dependent claim
            if context_lower.strip().endswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                return "Independent Claim"
            elif 'claim' in context_lower and any(word in context_lower for word in ['of claim', 'according to', 'wherein']):
                return "Dependent Claim"
            else:
                return "Claims Section"

        elif any(keyword in context_lower for keyword in ['background', 'prior art', 'field of invention']):
            return "Background/Prior Art"

        elif any(keyword in context_lower for keyword in ['summary', 'brief summary']):
            return "Summary of Invention"

        elif any(keyword in context_lower for keyword in ['detailed description', 'description of', 'embodiment']):
            return "Detailed Description"

        elif any(keyword in context_lower for keyword in ['abstract']):
            return "Abstract"

        elif any(keyword in context_lower for keyword in ['brief description', 'figures', 'drawings']):
            return "Brief Description of Drawings"

        # Check document structure for context
        claim_count = doc_lower.count('claim')
        if claim_count > 3:
            return "Claims Section"
        elif 'embodiment' in doc_lower:
            return "Detailed Description"
        else:
            return "General Patent Content"

    async def generate_suggestion(
        self,
        content: str,
        cursor_pos: int,
        context_before: str,
        context_after: str,
        suggestion_type: str = "completion"
    ) -> Dict[str, Any]:
        """
        Generate an inline suggestion based on full document context.

        Args:
            content: Full document HTML content
            cursor_pos: Current cursor position
            context_before: Text immediately before cursor
            context_after: Text immediately after cursor
            suggestion_type: Type of suggestion (completion, improvement, correction)

        Returns:
            Dict with suggested_text, reasoning, confidence, etc.
        """

        if not self.client:
            return {
                "suggested_text": "...",
                "reasoning": "API key not configured",
                "confidence": 0.0
            }

        try:
            # Build long-term memory context (cached)
            document_memory = self._build_document_memory(content)

            # Build present memory context (focused on immediate completion)
            immediate_context = self._get_immediate_context(context_before)

            # Use rich contextual prompt for high-quality completion
            user_prompt = self._build_rich_completion_prompt(document_memory, immediate_context)

            system_prompt = "You are a patent writing assistant. Complete the given text with 2-4 natural words only."

            response = self.client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": user_prompt
                }],
                max_tokens=15,  # Reduced for focused completion
                temperature=0.3  # Lower temperature for more focused responses
            )

            suggested_text = response.choices[0].message.content.strip()

            # Validate and clean the suggestion
            is_valid, cleaned_suggestion = self._validate_suggestion(suggested_text, immediate_context)

            if not is_valid:
                print(f"❌ Invalid suggestion rejected: {suggested_text} - {cleaned_suggestion}")
                return {
                    "suggested_text": "",
                    "reasoning": f"Suggestion validation failed: {cleaned_suggestion}",
                    "confidence": 0.0
                }

            print(f"✅ Valid suggestion generated: '{cleaned_suggestion}'")

            return {
                "suggested_text": cleaned_suggestion,
                "reasoning": f"AI word completion for {immediate_context['completion_type']} in {document_memory['technical_domain']}",
                "confidence": 0.85,
                "section_context": document_memory['technical_domain'],
                "completion_type": immediate_context['completion_type']
            }

        except Exception as e:
            print(f"OpenAI API error in inline suggestions: {e}")
            return {
                "suggested_text": "",
                "reasoning": "AI service temporarily unavailable",
                "confidence": 0.0
            }
