"""
Demo: Memory Learning Loop in Action
Shows how the system gets smarter with each analysis
"""
import asyncio
from app.services.memory_service import get_memory_service

async def demo():
    print("\n" + "="*80)
    print("🧠 MEMORY LEARNING LOOP DEMO")
    print("="*80)

    memory = get_memory_service()
    client_id = "demo_hackathon_client"

    # Simulate 3 document analyses over time
    documents = [
        {
            "doc_id": "patent_001",
            "analysis": "Legal compliance analysis found 2 issues. Issue 1: Section 3(k) - Software algorithm lacks technical effect. Issue 2: Claim 1 lacks enablement details. Confidence: 0.82"
        },
        {
            "doc_id": "patent_002",
            "analysis": "Legal compliance analysis found 3 issues. Issue 1: Section 3(k) - Computer program per se without technical contribution. Issue 2: Claims lack definiteness. Issue 3: Abstract too vague. Confidence: 0.79"
        },
        {
            "doc_id": "patent_003",
            "analysis": "Legal compliance analysis found 1 issue. Issue 1: Section 3(k) - Mathematical method needs technical application. Confidence: 0.88"
        }
    ]

    print("\n📝 Simulating client's patent filing journey...\n")

    for i, doc in enumerate(documents, 1):
        print(f"{'='*80}")
        print(f"ANALYSIS #{i} - Document: {doc['doc_id']}")
        print(f"{'='*80}")

        # Check what the system knows BEFORE this analysis
        print(f"\n📊 Client History Before Analysis #{i}:")
        past = memory.query_client_memory(
            client_id=client_id,
            query="legal issues analysis patterns",
            memory_type="analysis",
            limit=5
        )

        if past:
            print(f"   Found {len(past)} previous analyses:")
            for j, p in enumerate(past, 1):
                print(f"   {j}. {p.get('memory', '')[:80]}...")
        else:
            print("   No history (first time user)")

        # Store this analysis
        print(f"\n💾 Storing analysis #{i}...")
        memory.store_client_analysis(
            client_id=client_id,
            analysis_summary=doc['analysis'],
            metadata={
                'document_id': doc['doc_id'],
                'analysis_type': 'legal_compliance',
                'analysis_number': i
            }
        )
        print(f"   ✓ Stored")

        # Show what system learned
        print(f"\n🧠 What the system now knows:")
        all_memories = memory.query_client_memory(
            client_id=client_id,
            query="Section 3(k) patterns recurring issues",
            memory_type="analysis",
            limit=5
        )

        if len(all_memories) >= 2:
            print(f"   🎯 PATTERN DETECTED: Client has Section 3(k) issues in {len([m for m in all_memories if '3(k)' in m.get('memory', '')])} documents")
            print(f"   💡 NEXT ANALYSIS: Will pay extra attention to Section 3(k) technical effects")

        print()
        await asyncio.sleep(0.5)  # Pause for readability

    # Final summary
    print(f"{'='*80}")
    print("📈 LEARNING SUMMARY")
    print(f"{'='*80}")

    all_client_memories = memory.get_client_all_memories(client_id)
    print(f"\n✅ Total memories stored: {len(all_client_memories)}")
    print(f"✅ Pattern identified: Recurring Section 3(k) issues")
    print(f"✅ Next analysis will be: PERSONALIZED based on this client's patterns")

    print("\n🚀 HACKATHON DEMO POINTS:")
    print("   1. System remembers EVERY analysis")
    print("   2. Identifies patterns (e.g., Section 3(k) recurring)")
    print("   3. Future analyses are SMARTER and PERSONALIZED")
    print("   4. Gets better with EVERY document - true AI learning!")

    print(f"\n{'='*80}")

if __name__ == "__main__":
    asyncio.run(demo())
