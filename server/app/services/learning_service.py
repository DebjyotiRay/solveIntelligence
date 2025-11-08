"""
Learning Service - Captures and analyzes user behavior to improve suggestions

This service completes the learning loop by:
1. Capturing suggestion feedback (accept/reject/modify)
2. Extracting writing patterns from user behavior
3. Storing learned patterns in episodic memory
4. Providing personalized suggestions based on learning
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter
import re

from app.services.memory_service import get_memory_service

logger = logging.getLogger(__name__)


class LearningService:
    """Service for learning from user interactions and improving suggestions"""
    
    def __init__(self):
        self.memory = get_memory_service()
        logger.info("LearningService initialized")
    
    # ==================== FEEDBACK TRACKING ====================
    
    async def track_suggestion_feedback(
        self,
        client_id: str,
        suggestion_id: str,
        action: str,  # "accepted", "rejected", "modified"
        suggested_text: str,
        actual_text: Optional[str] = None,
        context_before: str = "",
        context_after: str = ""
    ) -> Dict[str, Any]:
        """
        Track user's response to a suggestion.
        
        Args:
            client_id: Unique client identifier
            suggestion_id: ID of the suggestion
            action: What user did (accepted/rejected/modified)
            suggested_text: What AI suggested
            actual_text: What user actually wrote (if modified)
            context_before: Text before suggestion
            context_after: Text after suggestion
            
        Returns:
            Dict with tracking result
        """
        try:
            feedback_data = {
                "suggestion_id": suggestion_id,
                "action": action,
                "suggested_text": suggested_text,
                "actual_text": actual_text or suggested_text,
                "context_before": context_before[-100:],  # Last 100 chars
                "context_after": context_after[:100],  # Next 100 chars
                "timestamp": datetime.now().isoformat(),
                "memory_type": "feedback"
            }
            
            # Store in episodic memory
            result = self.memory.store_client_preference(
                client_id=client_id,
                preference=f"Suggestion {action}: '{suggested_text[:50]}'",
                metadata=feedback_data
            )
            
            logger.info(f"Tracked {action} feedback for client {client_id}")
            
            # If rejected or modified, analyze why
            if action in ["rejected", "modified"] and actual_text:
                await self._learn_from_correction(
                    client_id=client_id,
                    suggested=suggested_text,
                    actual=actual_text,
                    context=context_before
                )
            
            return {"status": "tracked", "result": result}
            
        except Exception as e:
            logger.error(f"Failed to track feedback: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _learn_from_correction(
        self,
        client_id: str,
        suggested: str,
        actual: str,
        context: str
    ):
        """
        Analyze why user modified/rejected a suggestion and learn preferences.
        """
        try:
            # Extract patterns from the correction
            patterns = []
            
            # Check for word substitutions
            suggested_words = set(suggested.lower().split())
            actual_words = set(actual.lower().split())
            
            # Words user prefers
            preferred = actual_words - suggested_words
            # Words user avoids
            avoided = suggested_words - actual_words
            
            if preferred:
                pattern = f"Prefers: {', '.join(list(preferred)[:3])}"
                patterns.append(pattern)
            
            if avoided:
                pattern = f"Avoids: {', '.join(list(avoided)[:3])}"
                patterns.append(pattern)
            
            # Store learned patterns
            if patterns:
                for pattern in patterns:
                    self.memory.store_client_preference(
                        client_id=client_id,
                        preference=pattern,
                        metadata={
                            "pattern_type": "terminology",
                            "example_suggested": suggested,
                            "example_actual": actual,
                            "learned_from": "correction",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                
                logger.info(f"Learned {len(patterns)} patterns from correction")
                
        except Exception as e:
            logger.error(f"Failed to learn from correction: {e}")
    
    # ==================== PATTERN EXTRACTION ====================
    
    async def learn_from_session(
        self,
        client_id: str,
        document_text: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze user's writing session to extract patterns.
        
        Args:
            client_id: Client identifier
            document_text: Full document text written by user
            document_id: Optional document identifier
            
        Returns:
            Dict with learned patterns
        """
        try:
            patterns_learned = []
            
            # 1. Extract common phrases (3-5 word sequences)
            phrases = self._extract_common_phrases(document_text)
            if phrases:
                self.memory.store_client_preference(
                    client_id=client_id,
                    preference=f"Common phrases: {', '.join(phrases[:5])}",
                    metadata={
                        "pattern_type": "phrases",
                        "phrases": phrases,
                        "document_id": document_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                patterns_learned.append(f"phrases: {len(phrases)}")
            
            # 2. Detect structural patterns
            structure = self._analyze_structure(document_text)
            if structure:
                self.memory.store_client_preference(
                    client_id=client_id,
                    preference=f"Structure pattern: {structure}",
                    metadata={
                        "pattern_type": "structure",
                        "structure": structure,
                        "document_id": document_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                patterns_learned.append(f"structure: {structure}")
            
            # 3. Identify terminology preferences
            terminology = self._extract_terminology_preferences(document_text)
            if terminology:
                self.memory.store_client_preference(
                    client_id=client_id,
                    preference=f"Prefers terminology: {', '.join(list(terminology.keys())[:5])}",
                    metadata={
                        "pattern_type": "terminology",
                        "terms": terminology,
                        "document_id": document_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                patterns_learned.append(f"terminology: {len(terminology)}")
            
            logger.info(f"Learned from session: {patterns_learned}")
            
            return {
                "status": "learned",
                "patterns": patterns_learned,
                "client_id": client_id
            }
            
        except Exception as e:
            logger.error(f"Failed to learn from session: {e}")
            return {"status": "error", "error": str(e)}
    
    def _extract_common_phrases(self, text: str, min_frequency: int = 2) -> List[str]:
        """Extract frequently used 3-5 word phrases"""
        # Clean text
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Extract n-grams (3-5 words)
        phrases = []
        for n in [3, 4, 5]:
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                phrases.append(phrase)
        
        # Count frequencies
        phrase_counts = Counter(phrases)
        
        # Return phrases that appear multiple times
        common_phrases = [
            phrase for phrase, count in phrase_counts.most_common(10)
            if count >= min_frequency
        ]
        
        return common_phrases
    
    def _analyze_structure(self, text: str) -> str:
        """Analyze document structure patterns"""
        # Count claim-like structures
        claim_patterns = len(re.findall(r'\b(claim|wherein|comprising)\b', text.lower()))
        
        # Count sections
        section_patterns = len(re.findall(r'\b(section|article|subsection)\b', text.lower()))
        
        if claim_patterns > 5:
            return "claim-heavy"
        elif section_patterns > 3:
            return "section-referenced"
        else:
            return "narrative"
    
    def _extract_terminology_preferences(self, text: str) -> Dict[str, int]:
        """Extract commonly used technical terms"""
        # Common patent terminology
        patent_terms = [
            'device', 'apparatus', 'system', 'method', 'process',
            'comprising', 'including', 'wherein', 'whereby',
            'configured', 'adapted', 'arranged', 'operable'
        ]
        
        text_lower = text.lower()
        term_counts = {}
        
        for term in patent_terms:
            count = len(re.findall(rf'\b{term}\b', text_lower))
            if count > 0:
                term_counts[term] = count
        
        # Return top terms
        return dict(sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    # ==================== PATTERN RETRIEVAL ====================
    
    async def get_client_patterns(
        self,
        client_id: str,
        pattern_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve learned patterns for a client.
        
        Args:
            client_id: Client identifier
            pattern_type: Optional filter (phrases, terminology, structure)
            
        Returns:
            List of learned patterns
        """
        try:
            # Query episodic memory for patterns
            patterns = self.memory.query_client_memory(
                client_id=client_id,
                query="writing patterns terminology preferences",
                memory_type="preference" if pattern_type is None else None,
                limit=20
            )
            
            # Filter by pattern type if specified
            if pattern_type:
                patterns = [
                    p for p in patterns
                    if p.get('metadata', {}).get('pattern_type') == pattern_type
                ]
            
            logger.debug(f"Retrieved {len(patterns)} patterns for client {client_id}")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to retrieve patterns: {e}")
            return []
    
    async def get_suggestion_acceptance_rate(
        self,
        client_id: str,
        recent_count: int = 50
    ) -> Dict[str, Any]:
        """
        Calculate suggestion acceptance rate for a client.
        
        Args:
            client_id: Client identifier
            recent_count: Number of recent suggestions to analyze
            
        Returns:
            Dict with acceptance statistics
        """
        try:
            # Query feedback memories
            feedbacks = self.memory.query_client_memory(
                client_id=client_id,
                query="suggestion accepted rejected modified",
                memory_type="preference",
                limit=recent_count
            )
            
            # Count actions
            action_counts = Counter()
            for feedback in feedbacks:
                action = feedback.get('metadata', {}).get('action')
                if action:
                    action_counts[action] += 1
            
            total = sum(action_counts.values())
            if total == 0:
                return {
                    "acceptance_rate": 0.0,
                    "total_suggestions": 0,
                    "breakdown": {}
                }
            
            acceptance_rate = action_counts.get('accepted', 0) / total
            
            return {
                "acceptance_rate": round(acceptance_rate, 2),
                "total_suggestions": total,
                "breakdown": dict(action_counts),
                "recent_count": recent_count
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate acceptance rate: {e}")
            return {
                "acceptance_rate": 0.0,
                "total_suggestions": 0,
                "error": str(e)
            }
    
    # ==================== LEARNING INSIGHTS ====================
    
    async def get_learning_progress(
        self,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive learning progress for a client.
        
        Returns insights about what the AI has learned and how it's improving.
        """
        try:
            # Get all client memories
            all_memories = self.memory.get_client_all_memories(client_id)
            
            # Categorize memories
            documents = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'document']
            analyses = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'analysis']
            preferences = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'preference']
            feedbacks = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'feedback']
            
            # Get acceptance rate
            acceptance_stats = await self.get_suggestion_acceptance_rate(client_id)
            
            # Get learned patterns
            patterns = await self.get_client_patterns(client_id)
            
            progress = {
                "client_id": client_id,
                "total_memories": len(all_memories),
                "documents_processed": len(documents),
                "analyses_performed": len(analyses),
                "preferences_learned": len(preferences),
                "suggestions_tracked": len(feedbacks),
                "acceptance_rate": acceptance_stats.get('acceptance_rate', 0.0),
                "patterns_learned": len(patterns),
                "learning_stage": self._determine_learning_stage(
                    len(documents),
                    acceptance_stats.get('acceptance_rate', 0.0)
                )
            }
            
            logger.info(f"Learning progress for {client_id}: {progress['learning_stage']}")
            return progress
            
        except Exception as e:
            logger.error(f"Failed to get learning progress: {e}")
            return {
                "client_id": client_id,
                "error": str(e)
            }
    
    def _determine_learning_stage(self, doc_count: int, acceptance_rate: float) -> str:
        """Determine what stage of learning the AI is at for this client"""
        if doc_count == 0:
            return "new_user"
        elif doc_count < 3:
            return "initial_learning"
        elif doc_count < 5:
            return "pattern_recognition"
        elif acceptance_rate > 0.6:
            return "personalized"
        else:
            return "improving"


# Global instance accessor
_learning_service = None

def get_learning_service() -> LearningService:
    """Get the singleton LearningService instance"""
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service
