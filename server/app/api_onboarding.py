"""
Onboarding API: Upload firm's historical documents for learning.
This is SEPARATE from daily drafting - it's a one-time knowledge base setup.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import PyPDF2
import io
from app.services.memory_service import get_memory_service
from datetime import datetime

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/upload-firm-documents")
async def upload_firm_documents(
    client_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Upload historical firm documents for AI learning.

    Flow:
    1. Firm uploads 5-10 successful past patents
    2. System extracts text and stores in client memory
    3. AI learns firm's writing style, preferences, patterns
    4. Future drafting uses this knowledge

    Args:
        client_id: Firm/team identifier (e.g., "acme_law_firm")
        files: PDF files of past successful patents
    """
    memory = get_memory_service()
    results = []

    for file in files:
        try:
            # Extract text from PDF
            pdf_bytes = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()

            # Store in client memory
            result = memory.store_client_document(
                client_id=client_id,
                document_content=text[:10000],  # First 10k chars
                metadata={
                    'document_id': f"historical_{file.filename}",
                    'document_type': 'reference_patent',
                    'title': file.filename,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'onboarding_upload',
                    'status': 'successful'  # These are successful patents!
                }
            )

            # Extract patterns for learning
            patterns = extract_writing_patterns(text)
            for pattern in patterns:
                memory.store_client_preference(
                    client_id=client_id,
                    preference=pattern['description'],
                    metadata={
                        'pattern_type': pattern['type'],
                        'source_document': file.filename,
                        'confidence': 0.8
                    }
                )

            results.append({
                "filename": file.filename,
                "status": "success",
                "chars_stored": len(text[:10000]),
                "patterns_learned": len(patterns)
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "client_id": client_id,
        "total_files": len(files),
        "successful": len([r for r in results if r['status'] == 'success']),
        "results": results
    }


def extract_writing_patterns(text: str) -> List[dict]:
    """Extract reusable writing patterns from successful documents."""
    patterns = []

    # Pattern 1: Terminology preferences
    if "at least" in text and "substantially" not in text:
        patterns.append({
            'type': 'terminology',
            'description': 'Prefers specific measurements ("at least X%") over vague terms ("substantially")'
        })

    # Pattern 2: Claim structure
    if text.count("wherein") > 5:
        patterns.append({
            'type': 'claim_structure',
            'description': 'Uses "wherein" clauses for additional limitations in claims'
        })

    # Pattern 3: Section ordering
    if "BACKGROUND" in text and "SUMMARY" in text:
        patterns.append({
            'type': 'document_structure',
            'description': 'Follows standard patent structure: Background → Summary → Detailed Description'
        })

    return patterns


@router.get("/firm-knowledge/{client_id}")
async def get_firm_knowledge(client_id: str):
    """Get summary of what AI has learned about this firm."""
    memory = get_memory_service()

    # Get all client memories
    all_memories = memory.get_client_all_memories(client_id)

    # Categorize
    documents = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'document']
    preferences = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'preference']
    analyses = [m for m in all_memories if m.get('metadata', {}).get('memory_type') == 'analysis']

    return {
        "client_id": client_id,
        "total_memories": len(all_memories),
        "reference_documents": len(documents),
        "learned_preferences": len(preferences),
        "past_analyses": len(analyses),
        "preferences_summary": [
            {
                "pattern": p.get('memory', ''),
                "type": p.get('metadata', {}).get('pattern_type', 'unknown')
            }
            for p in preferences[:10]  # Top 10
        ]
    }
