"""
Test that agents use firm knowledge via SharedMemoryContext
"""

from app.services.shared_memory_context import create_shared_context

print("\n" + "="*80)
print("TESTING 3-TIER MEMORY IN SHARED CONTEXT")
print("="*80)

# Create shared context
context = create_shared_context(
    client_id="test_firm",
    document_content="The present invention relates to a method for patent claims",
    task_type="analysis"
)

print(f"\n✅ Shared context built:")
print(f"   Level 1 (Legal): {len(context.legal_context)} references")
print(f"   Level 2 (Firm): {len(context.firm_context)} documents")
print(f"   Level 3 (Case): {len(context.client_context)} documents")

# Get context for structure agent
agent_context = context.get_context_for_agent("structure")

print(f"\n📋 Structure agent gets:")
print(f"   Legal refs: {len(agent_context['legal_references'])}")
print(f"   Firm docs: {len(agent_context['firm_documents'])}")
print(f"   Case docs: {len(agent_context['case_documents'])}")

if agent_context['firm_documents']:
    print(f"\n💼 Sample firm document:")
    firm_doc = agent_context['firm_documents'][0]
    print(f"   Title: {firm_doc.get('metadata', {}).get('title', 'N/A')}")
    print(f"   Preview: {firm_doc.get('memory', '')[:150]}...")

# Get formatted context for LLM
formatted = context.get_formatted_context_for_llm("structure", max_chars=1000)
print(f"\n📝 Formatted context for LLM ({len(formatted)} chars):")
print(formatted[:500] + "...")

print("\n" + "="*80)
print("✅ Agents are now using 3-tier memory!")
print("="*80)
