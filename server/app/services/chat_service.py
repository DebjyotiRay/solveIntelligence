"""
Grounded Chat Service

Simple chatbot for users to discuss/clarify AI analysis.
Grounded in ChromaDB/mem0 memory for accurate, contextual responses.
"""

import logging
import openai
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.memory_service import get_memory_service

logger = logging.getLogger(__name__)


class GroundedChatService:
    """
    Chatbot service grounded in memory for discussing analysis results.

    Use case:
    - User disagrees with AI suggestion → opens chat
    - User asks "Why did you suggest X?" → chatbot retrieves relevant sources
    - User asks "Can you explain Section 3k?" → chatbot pulls from legal knowledge
    """

    def __init__(self):
        self.memory = get_memory_service()
        self.api_key = os.getenv("OPENAI_API_KEY")
        logger.info("Grounded Chat Service initialized")

    async def chat(
        self,
        user_message: str,
        client_id: str,
        document_id: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        document_context: Optional[str] = None,
        analysis_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message with memory-grounded response.

        Args:
            user_message: User's question/message
            client_id: Client ID for personalization
            document_id: Optional document being discussed
            conversation_history: Previous messages [{"role": "user", "content": "..."}]
            document_context: Optional current document content
            analysis_results: Optional AI analysis results (issues, scores, etc.)

        Returns:
            {
                "response": "AI response text",
                "sources": [{"id": 1, "citation": "...", "content": "..."}],
                "metadata": {...}
            }
        """

        logger.info(f"Chat request from client {client_id}: '{user_message[:50]}...'")

        if not self.api_key:
            return {
                "response": "Error: OpenAI API key not configured.",
                "sources": [],
                "metadata": {"error": "no_api_key"}
            }

        # Step 1: Retrieve relevant context from memory
        context_sources = await self._retrieve_grounded_context(
            user_message=user_message,
            client_id=client_id,
            document_context=document_context
        )

        logger.info(f"📚 Retrieved {len(context_sources)} sources for chat grounding")
        for idx, src in enumerate(context_sources[:3], 1):  # Log first 3
            logger.info(f"  Source {idx}: {src.get('tier')} - {src.get('citation')[:50]}")

        # Step 2: Build chat prompt with grounded context
        system_prompt = self._build_system_prompt(context_sources, document_context, analysis_results)

        # Step 3: Build conversation with history
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history[-6:])  # Last 6 messages for context

        messages.append({"role": "user", "content": user_message})

        # Step 4: Generate response
        try:
            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cheap for chat
                messages=messages,
                max_tokens=800,
                temperature=0.3
            )

            ai_response = response.choices[0].message.content.strip()

            logger.info(f"Chat response generated: {len(ai_response)} chars, {len(context_sources)} sources")
            logger.info(f"✅ Returning {len(context_sources)} sources to frontend")

            return {
                "response": ai_response,
                "sources": context_sources,
                "metadata": {
                    "sources_count": len(context_sources),
                    "timestamp": datetime.now().isoformat(),
                    "model": "gpt-4o-mini"
                }
            }

        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "sources": [],
                "metadata": {"error": str(e)}
            }

    async def _retrieve_grounded_context(
        self,
        user_message: str,
        client_id: str,
        document_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant sources from memory for grounding."""

        # Enhance query with document context if available
        query = user_message
        if document_context:
            query = f"{user_message} {document_context[:200]}"

        sources = []

        # Retrieve from legal knowledge (2 sources)
        legal_results = self.memory.query_legal_knowledge(query=query, limit=2)
        for i, result in enumerate(legal_results):
            sources.append({
                "id": len(sources) + 1,
                "citation": self._format_legal_citation(result.get('metadata', {})),
                "content": result.get('memory', '')[:300],
                "tier": "legal"
            })

        # Retrieve from firm knowledge (2 sources)
        firm_results = self.memory.query_firm_knowledge(query=query, limit=2)
        for result in firm_results:
            sources.append({
                "id": len(sources) + 1,
                "citation": self._format_firm_citation(result.get('metadata', {})),
                "content": result.get('memory', '')[:300],
                "tier": "firm"
            })

        # Retrieve from client memory (3 sources) - most relevant for personalization
        client_results = self.memory.query_client_memory(
            client_id=client_id,
            query=query,
            limit=3
        )
        for result in client_results:
            sources.append({
                "id": len(sources) + 1,
                "citation": self._format_client_citation(result.get('metadata', {})),
                "content": result.get('memory', '')[:300],
                "tier": "client"
            })

        logger.debug(f"Retrieved {len(sources)} sources for grounding")
        return sources

    def _build_system_prompt(
        self,
        sources: List[Dict[str, Any]],
        document_context: Optional[str],
        analysis_results: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build system prompt with grounded context."""

        base_prompt = """You are a helpful AI assistant specialized in patent law and analysis.

You help users understand and discuss patent analysis results. When users disagree with suggestions or have questions, you provide clear, grounded explanations.

IMPORTANT RULES:
1. Always reference the PROVIDED SOURCES below when answering
2. Use inline citations like [1], [2] when referencing sources
3. Be concise and clear
4. If you're uncertain, say so
5. Help users understand WHY suggestions were made, not just WHAT they are
"""

        # Add AI analysis results if available (PRIORITY CONTEXT!)
        if analysis_results:
            base_prompt += "\n\n=== AI ANALYSIS RESULTS ===\n"

            # Add overall metrics
            if 'total_issues' in analysis_results:
                base_prompt += f"Total Issues Found: {analysis_results['total_issues']}\n"
            if 'overall_score' in analysis_results:
                base_prompt += f"Overall Quality Score: {analysis_results['overall_score']:.1f}%\n"
            if 'agents_used' in analysis_results:
                base_prompt += f"Analysis By: {', '.join(analysis_results['agents_used'])}\n"

            # Add issues summary
            if 'analysis' in analysis_results and 'issues' in analysis_results['analysis']:
                issues = analysis_results['analysis']['issues']
                if issues:
                    base_prompt += f"\n📋 IDENTIFIED ISSUES ({len(issues)} total):\n"

                    # Group by severity
                    high_issues = [i for i in issues if i.get('severity') == 'high']
                    medium_issues = [i for i in issues if i.get('severity') == 'medium']
                    low_issues = [i for i in issues if i.get('severity') == 'low']

                    if high_issues:
                        base_prompt += f"\n🔴 HIGH SEVERITY ({len(high_issues)}):\n"
                        for idx, issue in enumerate(high_issues[:3], 1):  # Show top 3
                            base_prompt += f"  {idx}. [{issue.get('type', 'N/A')}] {issue.get('description', 'N/A')[:150]}\n"
                            base_prompt += f"     Suggestion: {issue.get('suggestion', 'N/A')[:150]}\n"

                    if medium_issues:
                        base_prompt += f"\n🟡 MEDIUM SEVERITY ({len(medium_issues)}):\n"
                        for idx, issue in enumerate(medium_issues[:3], 1):  # Show top 3
                            base_prompt += f"  {idx}. [{issue.get('type', 'N/A')}] {issue.get('description', 'N/A')[:150]}\n"

                    if low_issues:
                        base_prompt += f"\n🟢 LOW SEVERITY ({len(low_issues)}):\n"
                        for idx, issue in enumerate(low_issues[:2], 1):  # Show top 2
                            base_prompt += f"  {idx}. [{issue.get('type', 'N/A')}] {issue.get('description', 'N/A')[:100]}\n"

                    base_prompt += "\n(Use these issues to answer user questions about the analysis)\n"

            base_prompt += "=== END OF ANALYSIS RESULTS ===\n"

        # Add document context if available
        if document_context:
            base_prompt += f"\n\nCURRENT DOCUMENT CONTEXT:\n{document_context[:500]}\n"

        # Add retrieved sources
        if sources:
            base_prompt += "\n\nPROVIDED SOURCES (use these to ground your responses):\n"
            for src in sources:
                base_prompt += f"\n[{src['id']}] {src['content']}\nSource: {src['citation']}\n"

        base_prompt += "\n\nRespond to the user's question using the analysis results and sources above."

        return base_prompt

    def _format_legal_citation(self, meta: Dict) -> str:
        """Format legal citation."""
        source = meta.get('source', 'Legal Document')
        section = meta.get('section', '')
        return f"{source}, {section}" if section else source

    def _format_firm_citation(self, meta: Dict) -> str:
        """Format firm citation."""
        title = meta.get('title', 'Firm Document')
        year = meta.get('year', 'n.d.')
        return f"{title} (Firm Knowledge, {year})"

    def _format_client_citation(self, meta: Dict) -> str:
        """Format client citation."""
        title = meta.get('title', 'Client Document')
        doc_type = meta.get('document_type', 'document')
        stored_at = meta.get('stored_at', '')
        date = stored_at.split('T')[0] if stored_at else 'n.d.'
        return f"{title} ({doc_type}, {date})"


# Global instance
_chat_service = None

def get_chat_service() -> GroundedChatService:
    """Get singleton chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = GroundedChatService()
    return _chat_service
