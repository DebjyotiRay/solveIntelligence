"""
Quality Enhancement Functions for Patent Agents

These functions should be integrated into the existing agents to add
comprehensive grammar, style, and content quality validation.
"""

import re
import string
from typing import Dict, Any, List, Tuple
from collections import Counter


class ContentQualityValidator:
    """
    Comprehensive content quality validation for patent documents.
    Checks grammar, spelling, style, readability, and technical accuracy.
    """
    
    def __init__(self):
        # Common technical terms in patents (to avoid false spelling flags)
        self.patent_technical_terms = {
            'optogenetic', 'microprocessor', 'semiconductor', 'biocompatible',
            'nanotechnology', 'piezoelectric', 'magnetoresistive', 'photovoltaic',
            'superconductor', 'ferromagnetic', 'piezo', 'nano', 'micro', 'bio'
        }
        
        # Common patent language patterns
        self.patent_phrases = {
            'comprising', 'wherein', 'whereby', 'thereof', 'therefor',
            'heretofore', 'hereinafter', 'aforementioned'
        }

    def validate_content_quality(self, text: str, section: str = "document") -> Dict[str, Any]:
        """
        Comprehensive quality validation of text content.
        
        Args:
            text: Text to validate
            section: Section name for context
            
        Returns:
            Quality validation results with issues and scores
        """
        
        results = {
            "section": section,
            "grammar_issues": self.check_grammar_issues(text),
            "spelling_issues": self.check_spelling_issues(text),
            "style_issues": self.check_writing_style(text),
            "readability_score": self.calculate_readability_score(text),
            "technical_accuracy": self.check_technical_accuracy(text),
            "consistency_issues": self.check_terminology_consistency(text),
            "overall_quality_score": 0.0
        }
        
        # Calculate overall quality score
        results["overall_quality_score"] = self._calculate_quality_score(results)
        
        return results

    def check_grammar_issues(self, text: str) -> List[Dict[str, Any]]:
        """Check for common grammar issues in patent text."""
        
        issues = []
        sentences = re.split(r'[.!?]+', text)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 5:  # Skip very short fragments
                continue
                
            # Check subject-verb agreement (basic patterns)
            sv_issues = self._check_subject_verb_agreement(sentence)
            issues.extend([{**issue, "sentence": i+1} for issue in sv_issues])
            
            # Check tense consistency
            tense_issues = self._check_tense_consistency(sentence)
            issues.extend([{**issue, "sentence": i+1} for issue in tense_issues])
            
            # Check sentence structure
            structure_issues = self._check_sentence_structure(sentence)
            issues.extend([{**issue, "sentence": i+1} for issue in structure_issues])
        
        return issues

    def _check_subject_verb_agreement(self, sentence: str) -> List[Dict[str, Any]]:
        """Check basic subject-verb agreement patterns."""
        
        issues = []
        
        # Common problematic patterns
        patterns = [
            (r'\b(\w+s)\s+(are|were)\b', "Singular subject with plural verb"),
            (r'\b(this|that)\s+(are|were)\b', "Singular demonstrative with plural verb"),
            (r'\b(each|every|either|neither)\s+\w+\s+(are|were|have)\b', "Singular subjects with plural verbs"),
        ]
        
        for pattern, description in patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                issues.append({
                    "type": "subject_verb_agreement",
                    "description": description,
                    "severity": "medium",
                    "suggestion": "Check subject-verb agreement"
                })
        
        return issues

    def _check_tense_consistency(self, sentence: str) -> List[Dict[str, Any]]:
        """Check for tense consistency issues."""
        
        issues = []
        
        # Look for mixed tenses in same sentence (basic check)
        past_tense = len(re.findall(r'\b\w+ed\b', sentence))
        present_tense = len(re.findall(r'\b\w+(s|es)\b', sentence))
        
        if past_tense > 0 and present_tense > 0 and len(sentence.split()) > 10:
            issues.append({
                "type": "tense_inconsistency", 
                "description": "Mixed past and present tense in same sentence",
                "severity": "low",
                "suggestion": "Maintain consistent tense throughout sentence"
            })
        
        return issues

    def _check_sentence_structure(self, sentence: str) -> List[Dict[str, Any]]:
        """Check sentence structure quality."""
        
        issues = []
        words = sentence.split()
        
        # Check for overly long sentences
        if len(words) > 40:
            issues.append({
                "type": "long_sentence",
                "description": f"Very long sentence ({len(words)} words)",
                "severity": "medium",
                "suggestion": "Consider breaking into shorter sentences"
            })
        
        # Check for run-on sentences (multiple "and"/"or" conjunctions)
        conjunctions = len(re.findall(r'\b(and|or|but|yet|so)\b', sentence, re.IGNORECASE))
        if conjunctions > 3:
            issues.append({
                "type": "run_on_sentence",
                "description": f"Possible run-on sentence ({conjunctions} conjunctions)",
                "severity": "medium", 
                "suggestion": "Consider using shorter, more direct sentences"
            })
        
        return issues

    def check_spelling_issues(self, text: str) -> List[Dict[str, Any]]:
        """Check for potential spelling issues."""
        
        issues = []
        
        # Simple spelling checks (would need proper spell checker in production)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Check for repeated letters (potential typos)
        for word in words:
            if len(word) > 3:
                # Look for 3+ repeated letters (likely typos)
                if re.search(r'(.)\1{2,}', word):
                    issues.append({
                        "type": "potential_typo",
                        "word": word,
                        "description": f"Word with repeated letters: '{word}'",
                        "severity": "low",
                        "suggestion": "Check spelling"
                    })
        
        # Check for common typos in patent language
        common_typos = {
            'recieve': 'receive',
            'seperate': 'separate', 
            'definately': 'definitely',
            'occured': 'occurred',
            'begining': 'beginning'
        }
        
        for word in words:
            if word in common_typos:
                issues.append({
                    "type": "spelling_error",
                    "word": word,
                    "description": f"Misspelled word: '{word}'",
                    "severity": "medium",
                    "suggestion": f"Correct spelling: '{common_typos[word]}'"
                })
        
        return issues

    def check_writing_style(self, text: str) -> List[Dict[str, Any]]:
        """Check writing style and clarity issues."""
        
        issues = []
        
        # Check for passive voice overuse
        passive_voice_count = len(re.findall(r'\b(is|are|was|were|been|being)\s+\w+ed\b', text))
        total_sentences = len(re.split(r'[.!?]+', text))
        
        if total_sentences > 0:
            passive_ratio = passive_voice_count / total_sentences
            if passive_ratio > 0.5:  # More than 50% passive
                issues.append({
                    "type": "excessive_passive_voice",
                    "description": f"High use of passive voice ({passive_ratio:.1%})",
                    "severity": "medium",
                    "suggestion": "Consider using more active voice for clarity"
                })
        
        # Check for word repetition
        words = re.findall(r'\b\w{4,}\b', text.lower())  # Words 4+ letters
        word_counts = Counter(words)
        
        overused_words = [(word, count) for word, count in word_counts.items() 
                         if count > 5 and word not in self.patent_phrases]
        
        if overused_words:
            issues.append({
                "type": "word_repetition",
                "description": f"Overused words: {dict(overused_words)}",
                "severity": "low",
                "suggestion": "Use synonyms to improve variety"
            })
        
        # Check for unclear pronouns
        pronouns = len(re.findall(r'\b(this|that|these|those|it|they)\b', text, re.IGNORECASE))
        if pronouns > len(text.split()) * 0.05:  # More than 5% pronouns
            issues.append({
                "type": "unclear_pronouns",
                "description": "High use of pronouns may reduce clarity",
                "severity": "low",
                "suggestion": "Replace some pronouns with specific nouns for clarity"
            })
        
        return issues

    def calculate_readability_score(self, text: str) -> Dict[str, Any]:
        """Calculate readability metrics."""
        
        if not text or len(text.strip()) < 10:
            return {"score": 0.0, "grade_level": "N/A", "issues": ["Insufficient text"]}
        
        # Simple readability calculation (Flesch-Kincaid approximation)
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        syllables = self._count_syllables(text)
        
        if sentences == 0 or words == 0:
            return {"score": 0.0, "grade_level": "N/A", "issues": ["No complete sentences"]}
        
        avg_sentence_length = words / sentences
        avg_syllables_per_word = syllables / words
        
        # Flesch Reading Ease Score
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        flesch_score = max(0, min(100, flesch_score))  # Clamp to 0-100
        
        # Grade level approximation
        grade_level = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
        grade_level = max(1, grade_level)
        
        issues = []
        if flesch_score < 30:
            issues.append("Text is very difficult to read")
        elif flesch_score < 50:
            issues.append("Text may be challenging for general readers")
        
        if avg_sentence_length > 25:
            issues.append("Average sentence length is high")
        
        return {
            "flesch_score": round(flesch_score, 1),
            "grade_level": round(grade_level, 1),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2),
            "issues": issues
        }

    def _count_syllables(self, text: str) -> int:
        """Approximate syllable counting."""
        
        # Remove punctuation and convert to lowercase
        text = text.lower()
        text = ''.join(c for c in text if c.isalpha() or c.isspace())
        
        words = text.split()
        total_syllables = 0
        
        for word in words:
            syllables = len(re.findall(r'[aeiouAEIOU]', word))
            if word.endswith('e'):
                syllables -= 1
            if syllables == 0:
                syllables = 1
            total_syllables += syllables
        
        return total_syllables

    def check_technical_accuracy(self, text: str) -> List[Dict[str, Any]]:
        """Check for technical accuracy indicators."""
        
        issues = []
        
        # Check for vague technical terms
        vague_terms = ['device', 'system', 'apparatus', 'method', 'process', 'means']
        vague_count = 0
        
        for term in vague_terms:
            pattern = r'\b' + term + r'\b'
            count = len(re.findall(pattern, text, re.IGNORECASE))
            vague_count += count
        
        total_words = len(text.split())
        if total_words > 0 and vague_count / total_words > 0.02:  # More than 2% vague terms
            issues.append({
                "type": "vague_technical_terms",
                "description": "High use of vague technical terms",
                "severity": "medium",
                "suggestion": "Use more specific technical terminology"
            })
        
        # Check for unsupported technical claims
        claim_indicators = ['superior', 'optimal', 'best', 'maximum', 'minimum', 'perfect']
        for indicator in claim_indicators:
            if re.search(r'\b' + indicator + r'\b', text, re.IGNORECASE):
                issues.append({
                    "type": "unsupported_claim",
                    "description": f"Technical claim '{indicator}' may need support",
                    "severity": "low",
                    "suggestion": "Provide technical justification for claims"
                })
        
        return issues

    def check_terminology_consistency(self, text: str) -> List[Dict[str, Any]]:
        """Check for terminology consistency throughout document."""
        
        issues = []
        
        # Find technical terms (capitalized words, hyphenated terms)
        technical_terms = re.findall(r'\b[A-Z][a-z]+-[a-z]+\b|\b[A-Z]{2,}\b', text)
        
        # Look for potential inconsistencies (similar but different terms)
        term_variations = {}
        for term in technical_terms:
            base = term.lower().replace('-', '').replace('_', '')
            if base not in term_variations:
                term_variations[base] = []
            term_variations[base].append(term)
        
        # Flag terms with multiple variations
        for base, variations in term_variations.items():
            if len(set(variations)) > 1:  # Multiple different spellings/formats
                issues.append({
                    "type": "terminology_inconsistency",
                    "description": f"Inconsistent term usage: {list(set(variations))}",
                    "severity": "medium",
                    "suggestion": "Use consistent terminology throughout document"
                })
        
        return issues

    def _calculate_quality_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall content quality score."""
        
        # Start with perfect score
        score = 1.0
        
        # Deduct for issues
        grammar_penalty = len(results["grammar_issues"]) * 0.1
        spelling_penalty = len(results["spelling_issues"]) * 0.15
        style_penalty = len(results["style_issues"]) * 0.05
        technical_penalty = len(results["technical_accuracy"]) * 0.08
        consistency_penalty = len(results["consistency_issues"]) * 0.1
        
        # Factor in readability
        readability = results["readability_score"]
        if readability.get("flesch_score", 0) < 30:
            score -= 0.2
        elif readability.get("flesch_score", 0) < 50:
            score -= 0.1
        
        # Apply penalties
        score -= (grammar_penalty + spelling_penalty + style_penalty + 
                 technical_penalty + consistency_penalty)
        
        return max(0.0, score)


