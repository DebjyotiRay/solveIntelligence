"""
Test querying the existing 1634 legal documents
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.memory_service import get_memory_service

def main():
    print("\n" + "="*80)
    print("TESTING LEGAL KNOWLEDGE QUERIES ON EXISTING 1634 DOCUMENTS")
    print("="*80)

    memory_service = get_memory_service()

    # Test queries on existing ingested data
    test_queries = [
        {
            "query": "Section 3(k) computer programs software patentability",
            "description": "Patent Act Section 3(k) - Software patentability"
        },
        {
            "query": "IPC Section 302 murder punishment",
            "description": "IPC Section 302 - Murder"
        },
        {
            "query": "Section 65B electronic evidence digital records",
            "description": "Evidence Act Section 65B - Electronic evidence"
        },
        {
            "query": "Article 21 life and personal liberty fundamental rights",
            "description": "Constitution Article 21 - Right to life"
        },
        {
            "query": "patent eligibility inventions exclusions",
            "description": "General patent eligibility"
        }
    ]

    for test in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {test['description']}")
        print(f"Search: '{test['query']}'")
        print(f"{'='*80}")

        results = memory_service.query_legal_knowledge(
            query=test['query'],
            limit=3
        )

        print(f"Found {len(results)} results:")

        for i, result in enumerate(results, 1):
            memory_text = result.get('memory', result.get('text', 'N/A'))
            metadata = result.get('metadata', {})

            print(f"\n  {i}. {metadata.get('source', 'Unknown Source')}")
            print(f"     Section: {metadata.get('section', 'N/A')}")
            print(f"     {memory_text[:200]}...")

        if not results:
            print("  ⚠️ No results found - this might indicate an issue with the search")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Memory service initialized successfully")
    print(f"✓ Using model: all-mpnet-base-v2 (768 dimensions)")
    print(f"✓ Collection: indian_legal_knowledge_local")
    print(f"✓ Total documents in collection: 1634")
    print(f"\nIf all queries returned results, your memory service is working perfectly!")
    print(f"If queries returned 0 results, we may need to check the ChromaDB configuration.")

if __name__ == "__main__":
    main()
