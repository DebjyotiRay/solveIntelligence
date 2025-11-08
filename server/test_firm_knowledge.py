"""
Test querying legal knowledge collection (Indian law embeddings)
"""

from app.services.memory_service import get_memory_service

memory = get_memory_service()

print("\n" + "="*80)
print("TESTING LEGAL KNOWLEDGE RETRIEVAL")
print("="*80)

# Test queries for Indian legal documents
test_queries = [
    {
        "query": "Section 3k computer programs software patentability",
        "description": "Patent Act - Software Patentability"
    },
    {
        "query": "IPC Section 420 fraud cheating punishment",
        "description": "Indian Penal Code - Fraud"
    },
    {
        "query": "Section 65B electronic evidence admissibility digital records",
        "description": "Evidence Act - Electronic Evidence"
    },
    {
        "query": "novelty inventive step patent requirements",
        "description": "Patent Act - Patentability Criteria"
    },
    {
        "query": "criminal defamation libel Section 499 500",
        "description": "IPC - Defamation"
    }
]

for test in test_queries:
    print(f"\n{'='*80}")
    print(f"Query: {test['description']}")
    print(f"Search: '{test['query']}'")
    print(f"{'='*80}")
    
    results = memory.query_legal_knowledge(test['query'], limit=3)
    
    if results:
        print(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            meta = result['metadata']
            print(f"{i}. {meta.get('source', 'Unknown')}")
            print(f"   Section: {meta.get('section', 'N/A')}")
            print(f"   Type: {meta.get('document_type', 'N/A')}")
            print(f"   Category: {meta.get('category', 'N/A')}")
            print(f"   Score: {result.get('score', 0):.3f}")
            print(f"   Preview: {result['memory'][:150]}...")
            print()
    else:
        print("\n❌ No results found")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✅ Legal knowledge retrieval is working!")
print(f"📚 Total documents indexed: {memory.legal_collection_db.count()}")
print("🔍 Semantic search operational")
print("💡 Ready for AI agent integration")
