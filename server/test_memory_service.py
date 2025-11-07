"""
Test script for Memory Service
Tests basic operations of both unified legal memory and episodic client memory
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.memory_service import get_memory_service


async def test_unified_legal_memory():
    """Test unified legal memory operations"""
    print("\n" + "="*60)
    print("Testing Unified Legal Memory (Stage 1)")
    print("="*60)
    
    memory_service = get_memory_service()
    
    # Test 1: Add a sample legal document
    print("\n1. Adding sample Patent Act section...")
    try:
        memory_id = memory_service.add_legal_document(
            text="Section 3(k) of the Indian Patent Act states that a mathematical or business method or a computer program per se or algorithms are not inventions within the meaning of this Act.",
            metadata={
                'source': 'Indian Patent Act 1970',
                'section': '3(k)',
                'document_type': 'statute',
                'category': 'exclusions',
                'topic': 'software_patentability'
            }
        )
        print(f"✓ Successfully added legal document: {memory_id}")
    except Exception as e:
        print(f"✗ Failed to add legal document: {e}")
        return False
    
    # Test 2: Query the legal knowledge
    print("\n2. Querying legal knowledge about software patentability...")
    try:
        results = memory_service.query_legal_knowledge(
            query="software patentability Section 3(k)",
            limit=3
        )
        print(f"✓ Found {len(results)} results")
        if results:
            print(f"   First result: {results[0].get('memory', 'N/A')[:100]}...")
    except Exception as e:
        print(f"✗ Failed to query legal knowledge: {e}")
        return False
    
    # Test 3: Add another legal document
    print("\n3. Adding IPC section...")
    try:
        memory_service.add_legal_document(
            text="Section 302 of the Indian Penal Code deals with punishment for murder. Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
            metadata={
                'source': 'Indian Penal Code 1860',
                'section': '302',
                'document_type': 'criminal_law',
                'category': 'offences_against_body',
                'topic': 'murder'
            }
        )
        print("✓ Successfully added IPC section")
    except Exception as e:
        print(f"✗ Failed to add IPC section: {e}")
        return False
    
    # Test 4: Query with filters
    print("\n4. Querying with document type filter...")
    try:
        results = memory_service.query_legal_knowledge(
            query="punishment",
            limit=5,
            filters={'document_type': 'criminal_law'}
        )
        print(f"✓ Found {len(results)} criminal law results")
    except Exception as e:
        print(f"✗ Failed filtered query: {e}")
        return False
    
    print("\n✓ Unified Legal Memory tests passed!")
    return True


async def test_episodic_client_memory():
    """Test episodic client memory operations"""
    print("\n" + "="*60)
    print("Testing Episodic Client Memory (Stage 2)")
    print("="*60)
    
    memory_service = get_memory_service()
    test_client_id = "test_client_123"
    
    # Test 1: Store client document
    print(f"\n1. Storing patent document for client {test_client_id}...")
    try:
        doc_memory_id = memory_service.store_client_document(
            client_id=test_client_id,
            document_content="A method for processing data using artificial intelligence comprising: receiving input data, processing the data using a neural network, and outputting results.",
            metadata={
                'document_id': 'patent_001',
                'document_type': 'patent',
                'title': 'AI-based Data Processing System',
                'section': 'claims'
            }
        )
        print(f"✓ Successfully stored client document: {doc_memory_id}")
    except Exception as e:
        print(f"✗ Failed to store client document: {e}")
        return False
    
    # Test 2: Store analysis result
    print(f"\n2. Storing analysis result for client {test_client_id}...")
    try:
        analysis_memory_id = memory_service.store_client_analysis(
            client_id=test_client_id,
            analysis_summary="Legal compliance analysis found potential Section 3(k) issue with AI method. Recommend adding technical implementation details.",
            metadata={
                'document_id': 'patent_001',
                'analysis_type': 'legal_compliance',
                'issues_found': 1,
                'confidence': 0.85
            }
        )
        print(f"✓ Successfully stored analysis: {analysis_memory_id}")
    except Exception as e:
        print(f"✗ Failed to store analysis: {e}")
        return False
    
    # Test 3: Store client preference
    print(f"\n3. Storing client preference...")
    try:
        pref_memory_id = memory_service.store_client_preference(
            client_id=test_client_id,
            preference="Client prefers detailed technical descriptions in patent claims",
            metadata={'preference_type': 'writing_style'}
        )
        print(f"✓ Successfully stored preference: {pref_memory_id}")
    except Exception as e:
        print(f"✗ Failed to store preference: {e}")
        return False
    
    # Test 4: Query client memory
    print(f"\n4. Querying client memory...")
    try:
        results = memory_service.query_client_memory(
            client_id=test_client_id,
            query="AI patent analysis",
            limit=5
        )
        print(f"✓ Found {len(results)} client memories")
        if results:
            print(f"   Sample: {results[0].get('memory', 'N/A')[:80]}...")
    except Exception as e:
        print(f"✗ Failed to query client memory: {e}")
        return False
    
    # Test 5: Query with memory type filter
    print(f"\n5. Querying only analysis memories...")
    try:
        results = memory_service.query_client_memory(
            client_id=test_client_id,
            query="analysis",
            memory_type='analysis',
            limit=5
        )
        print(f"✓ Found {len(results)} analysis memories")
    except Exception as e:
        print(f"✗ Failed filtered client query: {e}")
        return False
    
    # Test 6: Get all client memories
    print(f"\n6. Getting all memories for client...")
    try:
        all_memories = memory_service.get_client_all_memories(test_client_id)
        print(f"✓ Client has {len(all_memories)} total memories")
    except Exception as e:
        print(f"✗ Failed to get all memories: {e}")
        return False
    
    print("\n✓ Episodic Client Memory tests passed!")
    return True


async def test_cross_client_isolation():
    """Test that different clients have isolated memories"""
    print("\n" + "="*60)
    print("Testing Cross-Client Isolation")
    print("="*60)
    
    memory_service = get_memory_service()
    
    # Store data for client A
    print("\n1. Storing data for Client A...")
    memory_service.store_client_document(
        client_id="client_a",
        document_content="Client A's confidential patent about solar panels",
        metadata={'document_id': 'doc_a1'}
    )
    
    # Store data for client B
    print("2. Storing data for Client B...")
    memory_service.store_client_document(
        client_id="client_b",
        document_content="Client B's confidential patent about wind turbines",
        metadata={'document_id': 'doc_b1'}
    )
    
    # Query client A's memories
    print("\n3. Querying Client A's memories...")
    results_a = memory_service.query_client_memory(
        client_id="client_a",
        query="patent",
        limit=10
    )
    
    # Query client B's memories
    print("4. Querying Client B's memories...")
    results_b = memory_service.query_client_memory(
        client_id="client_b",
        query="patent",
        limit=10
    )
    
    print(f"\nClient A has {len(results_a)} memories")
    print(f"Client B has {len(results_b)} memories")
    
    # Verify isolation
    if results_a and results_b:
        a_content = str(results_a[0])
        b_content = str(results_b[0])
        
        if "solar" in a_content.lower() and "wind" not in a_content.lower():
            print("✓ Client A sees only their data")
        else:
            print("✗ Client A might see Client B's data")
            return False
        
        if "wind" in b_content.lower() and "solar" not in b_content.lower():
            print("✓ Client B sees only their data")
        else:
            print("✗ Client B might see Client A's data")
            return False
    
    print("\n✓ Cross-client isolation test passed!")
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Memory Service Test Suite")
    print("="*60)
    
    try:
        # Test unified legal memory
        legal_success = await test_unified_legal_memory()
        
        # Test episodic client memory
        client_success = await test_episodic_client_memory()
        
        # Test cross-client isolation
        isolation_success = await test_cross_client_isolation()
        
        # Summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Unified Legal Memory: {'✓ PASS' if legal_success else '✗ FAIL'}")
        print(f"Episodic Client Memory: {'✓ PASS' if client_success else '✗ FAIL'}")
        print(f"Cross-Client Isolation: {'✓ PASS' if isolation_success else '✗ FAIL'}")
        
        if legal_success and client_success and isolation_success:
            print("\n🎉 All tests passed! Memory service is working correctly.")
            print("\nNext steps:")
            print("1. Download legal PDFs (Patent Act, IPC)")
            print("2. Create document processing pipeline")
            print("3. Populate unified legal memory")
            print("4. Integrate with agents and inline suggestions")
            return True
        else:
            print("\n❌ Some tests failed. Please check the errors above.")
            return False
            
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set in environment")
        print("Please set it in your .env file")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
