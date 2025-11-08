"""
Mem0 Memory Service - Two-Stage Memory Architecture

Stage 1: Unified Legal Memory (Global)
- Indian Patent Act, IPC, Constitution, Case Law
- Shared across all clients

Stage 2: Episodic Client Memory (Per-Client)  
- Client's documents, analysis history, preferences
- Personalized and dynamic
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from mem0 import Memory
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Unified memory service managing both:
    1. Unified Legal Memory (global knowledge base)
    2. Episodic Client Memory (per-client personalization)
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - only one instance across the application"""
        if cls._instance is None:
            cls._instance = super(MemoryService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize dual-stage memory architecture"""
        if self._initialized:
            return
            
        logger.info("Initializing Memory Service with dual-stage architecture")
        
        # Configuration from environment
        self.legal_collection = os.getenv("MEM0_LEGAL_COLLECTION", "unified_legal_knowledge")
        self.client_collection = os.getenv("MEM0_CLIENT_COLLECTION", "episodic_client_memory")
        self.embedding_model_name = "all-mpnet-base-v2"  # Match ingested embeddings
        self.llm_model = os.getenv("MEM0_LLM_MODEL", "gpt-4o-mini")

        # Initialize Stage 1: Direct ChromaDB access for legal knowledge (ingested directly)
        logger.info("Initializing direct ChromaDB access for legal knowledge")
        self.chroma_client = chromadb.PersistentClient(
            path="db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Level 1: Legal Knowledge (Global)
        self.legal_collection_db = self.chroma_client.get_or_create_collection(
            name="indian_legal_knowledge_local",
            metadata={"description": "Indian legal knowledge base", "level": "1_legal"}
        )

        # Level 2: Firm Knowledge (Firm-wide)
        self.firm_collection_db = self.chroma_client.get_or_create_collection(
            name="firm_knowledge_local",
            metadata={"description": "Firm knowledge base", "level": "2_firm"}
        )

        # Use local_files_only to prevent network calls in Docker
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name, local_files_only=True)
            logger.info(f"✓ Loaded embedding model from cache: {self.embedding_model_name}")
        except Exception as e:
            logger.warning(f"Could not load model from cache, downloading: {e}")
            # If not cached, download (will work outside Docker or with proper network)
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"✓ Downloaded and loaded embedding model: {self.embedding_model_name}")

        legal_count = self.legal_collection_db.count()
        firm_count = self.firm_collection_db.count()

        if legal_count > 0:
            logger.info(f"✓ Level 1 (Legal) collection loaded: {legal_count} documents")
        else:
            logger.warning("⚠ Legal collection empty - run ingest_indian_laws_from_pdf.py")

        if firm_count > 0:
            logger.info(f"✓ Level 2 (Firm) collection loaded: {firm_count} documents")
        else:
            logger.info("ℹ️ Firm collection empty - add PDFs to data/firm_knowledge/ and run ingestion")

        # Note: We don't use Mem0 for Level 1 & 2 (legal + firm knowledge)
        # This avoids the overhead of Mem0's LLM processing for static documents
        self.unified_legal_memory = None  # Not used

        # Initialize Stage 2: Episodic Client Memory with Mem0 (needs LLM processing)
        try:
            self.episodic_client_memory = Memory.from_config({
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": self.client_collection,
                        "path": "db"
                    }
                },
                "embedder": {
                    "provider": "huggingface",  # LOCAL embeddings (FREE!)
                    "config": {
                        "model": "all-mpnet-base-v2"  # Same model for consistency (768 dimensions)
                    }
                },
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": self.llm_model,
                        "temperature": 0.1
                    }
                }
            })
            logger.info(f"✓ Episodic Client Memory initialized with LOCAL embeddings (model: all-mpnet-base-v2, collection: {self.client_collection})")
        except Exception as e:
            logger.error(f"Failed to initialize Episodic Client Memory: {e}")
            raise
        
        self._initialized = True
        logger.info("Memory Service fully initialized and ready")
    
    # ==================== UNIFIED LEGAL MEMORY (Stage 1) ====================
    
    def add_legal_document(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add document chunk to unified legal knowledge base directly to ChromaDB.

        Note: Legal documents are typically pre-ingested in batch.
        This method is mainly for testing or adding new legal references.

        Args:
            text: Legal document text (section, article, case law)
            metadata: {
                'source': 'Indian Patent Act',
                'section': '3(k)',
                'document_type': 'statute',
                'category': 'exclusions'
            }

        Returns:
            Dict with operation result
        """
        try:
            import uuid

            # Generate embedding
            embedding = self.embedding_model.encode(text, convert_to_tensor=False).tolist()

            # Generate unique ID
            doc_id = f"legal_{uuid.uuid4().hex[:12]}"

            # Add directly to ChromaDB
            self.legal_collection_db.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )

            logger.info(f"Added legal document: {metadata.get('source', 'Unknown')} - {metadata.get('section', '')}")
            return {"id": doc_id, "status": "added"}
        except Exception as e:
            logger.error(f"Failed to add legal document: {e}")
            raise
    
    def query_legal_knowledge(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search unified legal knowledge base using direct ChromaDB query.

        Args:
            query: Search query (e.g., "Section 3k software patentability")
            limit: Max results to return
            filters: Optional filters like {'document_type': 'statute'}

        Returns:
            List of relevant legal references with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=False).tolist()

            # Convert filters to ChromaDB format if provided
            where_filter = None
            if filters and len(filters) > 0:
                where_filter = self._format_filters_for_chromadb(filters)

            # Query ChromaDB directly
            results = self.legal_collection_db.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results to match Mem0-style output for consistency
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'memory': results['documents'][0][i],  # Full document text
                        'metadata': results['metadatas'][0][i],
                        'score': 1 - results['distances'][0][i] if results['distances'] else None  # Convert distance to similarity
                    })

            logger.debug(f"Legal knowledge search '{query}': {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Legal knowledge search failed: {e}")
            return []

    def query_firm_knowledge(
        self,
        query: str,
        limit: int = 5,
        firm_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search firm knowledge base using direct ChromaDB query.

        Args:
            query: Search query (e.g., "successful software patent claims")
            limit: Max results to return
            firm_id: Optional filter by firm_id (if you have multiple firms)

        Returns:
            List of relevant firm references with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=False).tolist()

            # Build filters if firm_id specified
            where_filter = None
            if firm_id:
                where_filter = {'firm_id': {'$eq': firm_id}}

            # Query ChromaDB directly
            results = self.firm_collection_db.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results to match Mem0-style output for consistency
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'memory': results['documents'][0][i],  # Full document text
                        'metadata': results['metadatas'][0][i],
                        'score': 1 - results['distances'][0][i] if results['distances'] else None  # Convert distance to similarity
                    })

            logger.debug(f"Firm knowledge search '{query}': {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Firm knowledge search failed: {e}")
            return []

    def get_all_legal_memories(self) -> List[Dict[str, Any]]:
        """Get all legal memories (for debugging/export)"""
        try:
            result = self.unified_legal_memory.get_all(agent_id="indian_legal_knowledge")
            # Extract results from the response
            return result.get('results', []) if isinstance(result, dict) else []
        except Exception as e:
            logger.error(f"Failed to get all legal memories: {e}")
            return []
    
    # ==================== EPISODIC CLIENT MEMORY (Stage 2) ====================
    
    def store_client_document(
        self,
        client_id: str,
        document_content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store client's patent document in their episodic memory using proper message format.

        Args:
            client_id: Unique client identifier
            document_content: Patent text (claims, description, etc.)
            metadata: {
                'document_id': 'doc_123',
                'document_type': 'patent',
                'title': 'AI-based system',
                'timestamp': '2025-01-07T...'
            }

        Returns:
            Dict with memory operation result
        """
        try:
            # Add client_id to metadata for filtering
            metadata['client_id'] = client_id
            metadata['memory_type'] = 'document'
            metadata['stored_at'] = datetime.now().isoformat()

            # CORRECTED: Use proper Mem0 message format (list of dicts)
            messages = [
                {
                    "role": "user",
                    "content": f"Store my patent document: {metadata.get('title', 'Untitled')}"
                },
                {
                    "role": "assistant",
                    "content": f"Document stored: {document_content[:500]}"  # First 500 chars
                }
            ]

            result = self.episodic_client_memory.add(
                messages=messages,
                user_id=client_id,
                metadata=metadata
            )

            logger.info(f"Stored document for client {client_id}: {metadata.get('document_id', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to store client document: {e}")
            raise
    
    def store_client_analysis(
        self,
        client_id: str,
        analysis_summary: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store analysis results in client's episodic memory using proper message format.

        Args:
            client_id: Unique client identifier
            analysis_summary: Summary of analysis performed
            metadata: {
                'document_id': 'doc_123',
                'analysis_type': 'legal_compliance',
                'issues_found': 3,
                'confidence': 0.85
            }

        Returns:
            Dict with memory operation result
        """
        try:
            metadata['client_id'] = client_id
            metadata['memory_type'] = 'analysis'
            metadata['timestamp'] = datetime.now().isoformat()

            # CORRECTED: Use proper Mem0 conversational format
            messages = [
                {
                    "role": "user",
                    "content": f"Analyze document {metadata.get('document_id', 'unknown')} for legal compliance"
                },
                {
                    "role": "assistant",
                    "content": analysis_summary
                }
            ]

            result = self.episodic_client_memory.add(
                messages=messages,
                user_id=client_id,
                metadata=metadata
            )

            logger.info(f"Stored analysis for client {client_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store client analysis: {e}")
            raise
    
    def store_client_preference(
        self,
        client_id: str,
        preference: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Store client preference or pattern using proper message format.

        Args:
            client_id: Unique client identifier
            preference: Preference description (e.g., "prefers British spelling")
            metadata: Optional additional metadata

        Returns:
            Dict with memory operation result
        """
        try:
            meta = metadata or {}
            meta['client_id'] = client_id
            meta['memory_type'] = 'preference'
            meta['timestamp'] = datetime.now().isoformat()

            # CORRECTED: Use proper Mem0 conversational format
            messages = [
                {
                    "role": "user",
                    "content": "Remember my writing preferences"
                },
                {
                    "role": "assistant",
                    "content": f"I'll remember: {preference}"
                }
            ]

            result = self.episodic_client_memory.add(
                messages=messages,
                user_id=client_id,
                metadata=meta
            )

            logger.info(f"Stored preference for client {client_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store client preference: {e}")
            raise
    
    def query_client_memory(
        self,
        client_id: str,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search client's episodic memory.

        Args:
            client_id: Client identifier
            query: Search query
            memory_type: Filter by type ('document', 'analysis', 'preference')
            limit: Max results

        Returns:
            List of relevant client memories
        """
        try:
            # Convert filters to ChromaDB format if needed
            chroma_filters = None
            if memory_type:
                chroma_filters = self._format_filters_for_chromadb({'memory_type': memory_type})

            result = self.episodic_client_memory.search(
                query=query,
                user_id=client_id,
                limit=limit,
                filters=chroma_filters
            )

            # Extract results from the response (Mem0 1.0.0 returns dict with 'results' key)
            memories = result.get('results', []) if isinstance(result, dict) else []
            logger.debug(f"Client {client_id} memory search '{query}': {len(memories)} results")
            return memories
        except Exception as e:
            logger.error(f"Client memory search failed: {e}")
            return []
    
    def get_client_all_memories(
        self,
        client_id: str
    ) -> List[Dict[str, Any]]:
        """Get all memories for a specific client"""
        try:
            result = self.episodic_client_memory.get_all(user_id=client_id)
            # Extract results from the response
            return result.get('results', []) if isinstance(result, dict) else []
        except Exception as e:
            logger.error(f"Failed to get client memories: {e}")
            return []
    
    def delete_client_memory(
        self,
        client_id: str,
        memory_id: str
    ) -> bool:
        """Delete a specific client memory"""
        try:
            self.episodic_client_memory.delete(memory_id=memory_id)
            logger.info(f"Deleted memory {memory_id} for client {client_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete client memory: {e}")
            return False
    
    def clear_client_memories(
        self,
        client_id: str
    ) -> bool:
        """Clear all memories for a specific client"""
        try:
            self.episodic_client_memory.delete_all(user_id=client_id)
            logger.info(f"Cleared all memories for client {client_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear client memories: {e}")
            return False

    # ==================== HELPER METHODS ====================

    def _format_filters_for_chromadb(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert simple filters to ChromaDB query format.

        ChromaDB requires operators like $eq, $and, $or.
        This converts {'key': 'value'} to {'key': {'$eq': 'value'}}

        Args:
            filters: Simple key-value filters

        Returns:
            ChromaDB-formatted filters
        """
        if not filters:
            return None

        # Single filter
        if len(filters) == 1:
            key, value = list(filters.items())[0]
            return {key: {'$eq': value}}

        # Multiple filters - use $and
        filter_list = []
        for key, value in filters.items():
            filter_list.append({key: {'$eq': value}})

        return {'$and': filter_list}


# Global instance accessor
def get_memory_service() -> MemoryService:
    """Get the singleton MemoryService instance"""
    return MemoryService()
