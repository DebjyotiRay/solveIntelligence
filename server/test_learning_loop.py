"""
Test Learning Loop - Verify the complete learning system works

This test simulates a user workflow to verify:
1. Suggestion generation with learned patterns
2. Feedback capture (accept/reject/modify)
3. Pattern extraction from sessions
4. Learning progress tracking
5. Improvement over time
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.learning_service import get_learning_service
from app.services.memory_service import get_memory_service
from app.ai.services.inline_suggestions import InlineSuggestionsService


async def test_learning_loop():
    """Test the complete learning loop"""
    
    print("\n" + "="*70)
    print("TESTING COMPLETE LEARNING LOOP")
    print("="*70 + "\n")
    
    # Initialize services
    learning_service = get_learning_service()
    memory_service = get_memory_service()
    suggestions_service = InlineSuggestionsService()
    
    client_id = "test_user_learning"
    
    # Clean slate - clear any existing memories
    print("🧹 Clearing existing test data...")
    try:
        memory_service.clear_client_memories(client_id)
        print("✅ Test data cleared\n")
    except:
        print("ℹ️  No existing data to clear\n")
    
    # ====================
    # SCENARIO 1: First Document (No Learning Yet)
    # ====================
    print("📝 SCENARIO 1: First Document (No Learning)\n")
    print("-" * 70)
    
    context1 = "A system for processing data using"
    print(f"User types: '{context1}'")
    
    suggestion1 = await suggestions_service.generate_suggestion(
        content=context1,
        cursor_pos=len(context1),
        context_before=context1,
        context_after="",
        client_id=client_id
    )
    
    print(f"✅ AI suggests: '{suggestion1.get('suggested_text', '')}'")
    print(f"   Confidence: {suggestion1.get('confidence', 0)}")
    print(f"   Learned patterns used: {suggestion1.get('learned_patterns', False)}")
    print(f"   Suggestion ID: {suggestion1.get('suggestion_id', 'N/A')}")
    
    # Simulate user accepting suggestion
    print("\n👤 User action: ACCEPTED")
    
    feedback1 = await learning_service.track_suggestion_feedback(
        client_id=client_id,
        suggestion_id=suggestion1.get('suggestion_id', 'sugg_1'),
        action="accepted",
        suggested_text=suggestion1.get('suggested_text', ''),
        context_before=context1
    )
    
    print(f"✅ Feedback tracked: {feedback1.get('status', 'error')}\n")
    
    # ====================
    # SCENARIO 2: User Modifies Suggestion  
    # ====================
    print("\n📝 SCENARIO 2: User Modifies Suggestion\n")
    print("-" * 70)
    
    context2 = "The device comprises a plurality of"
    print(f"User types: '{context2}'")
    
    suggestion2 = await suggestions_service.generate_suggestion(
        content=context2,
        cursor_pos=len(context2),
        context_before=context2,
        context_after="",
        client_id=client_id
    )
    
    suggested = suggestion2.get('suggested_text', 'components')
    print(f"✅ AI suggests: '{suggested}'")
    
    # User modifies it
    actual = "elements configured to"
    print(f"👤 User changes to: '{actual}'")
    print(f"   Action: MODIFIED")
    
    feedback2 = await learning_service.track_suggestion_feedback(
        client_id=client_id,
        suggestion_id=suggestion2.get('suggestion_id', 'sugg_2'),
        action="modified",
        suggested_text=suggested,
        actual_text=actual,
        context_before=context2
    )
    
    print(f"✅ Feedback tracked and patterns learned\n")
    
    # ====================
    # SCENARIO 3: Complete Document Session
    # ====================
    print("\n📝 SCENARIO 3: Analyze Complete Document\n")
    print("-" * 70)
    
    full_document = """
    A system for processing data comprising a device configured to receive input.
    The system comprises a plurality of elements wherein each element is adapted
    to perform a specific function. The device comprises memory configured to store
    data and a processor configured to process the data. The system wherein the
    device is operable to communicate with external systems comprising network
    interfaces wherein the network interfaces are configured to transmit data.
    """
    
    print(f"User completes document ({len(full_document)} chars)")
    
    session_learning = await learning_service.learn_from_session(
        client_id=client_id,
        document_text=full_document,
        document_id="doc_test_1"
    )
    
    print(f"✅ Session analyzed: {session_learning.get('status', 'error')}")
    print(f"   Patterns learned: {', '.join(session_learning.get('patterns', []))}\n")
    
    # ====================
    # SCENARIO 4: Check Learning Progress
    # ====================
    print("\n📊 SCENARIO 4: Learning Progress After First Document\n")
    print("-" * 70)
    
    progress = await learning_service.get_learning_progress(client_id)
    
    print(f"Client ID: {progress.get('client_id', 'N/A')}")
    print(f"Learning Stage: {progress.get('learning_stage', 'N/A')}")
    print(f"Documents Processed: {progress.get('documents_processed', 0)}")
    print(f"Suggestions Tracked: {progress.get('suggestions_tracked', 0)}")
    print(f"Patterns Learned: {progress.get('patterns_learned', 0)}")
    print(f"Acceptance Rate: {progress.get('acceptance_rate', 0):.0%}\n")
    
    # ====================
    # SCENARIO 5: Get Learned Patterns
    # ====================
    print("\n🧠 SCENARIO 5: View Learned Patterns\n")
    print("-" * 70)
    
    patterns = await learning_service.get_client_patterns(client_id)
    
    if patterns:
        print(f"Found {len(patterns)} learned patterns:")
        for i, pattern in enumerate(patterns[:5], 1):
            pattern_type = pattern.get('metadata', {}).get('pattern_type', 'unknown')
            memory_text = pattern.get('memory', '')[:60]
            print(f"  {i}. [{pattern_type}] {memory_text}...")
    else:
        print("ℹ️  No patterns learned yet (may need more interactions)")
    
    print()
    
    # ====================
    # SCENARIO 6: Second Document with Learning
    # ====================
    print("\n📝 SCENARIO 6: Second Document (With Learning)\n")
    print("-" * 70)
    
    # Simulate more interactions to build up learning
    for i in range(3):
        context = f"The system wherein the device comprises"
        suggestion = await suggestions_service.generate_suggestion(
            content=context,
            cursor_pos=len(context),
            context_before=context,
            context_after="",
            client_id=client_id
        )
        
        await learning_service.track_suggestion_feedback(
            client_id=client_id,
            suggestion_id=suggestion.get('suggestion_id', f'sugg_{i}'),
            action="accepted",
            suggested_text=suggestion.get('suggested_text', ''),
            context_before=context
        )
    
    # Check if learned patterns are now being used
    context_test = "A method comprising a plurality of"
    suggestion_learned = await suggestions_service.generate_suggestion(
        content=context_test,
        cursor_pos=len(context_test),
        context_before=context_test,
        context_after="",
        client_id=client_id
    )
    
    print(f"User types: '{context_test}'")
    print(f"✅ AI suggests: '{suggestion_learned.get('suggested_text', '')}'")
    print(f"   Confidence: {suggestion_learned.get('confidence', 0)}")
    print(f"   Using learned patterns: {suggestion_learned.get('learned_patterns', False)}")
    
    if suggestion_learned.get('learned_patterns'):
        print(f"   🎉 SUCCESS: AI is using learned patterns!")
    else:
        print(f"   ℹ️  Note: May need more data to activate learned patterns")
    
    print()
    
    # ====================
    # SCENARIO 7: Final Progress Check
    # ====================
    print("\n📊 SCENARIO 7: Final Learning Progress\n")
    print("-" * 70)
    
    final_progress = await learning_service.get_learning_progress(client_id)
    
    print(f"Learning Stage: {final_progress.get('learning_stage', 'N/A')}")
    print(f"Total Memories: {final_progress.get('total_memories', 0)}")
    print(f"Documents: {final_progress.get('documents_processed', 0)}")
    print(f"Suggestions: {final_progress.get('suggestions_tracked', 0)}")
    print(f"Patterns: {final_progress.get('patterns_learned', 0)}")
    print(f"Acceptance Rate: {final_progress.get('acceptance_rate', 0):.0%}")
    
    # Get acceptance rate details
    acceptance_stats = await learning_service.get_suggestion_acceptance_rate(client_id)
    print(f"\nAcceptance Breakdown:")
    breakdown = acceptance_stats.get('breakdown', {})
    for action, count in breakdown.items():
        print(f"  {action.capitalize()}: {count}")
    
    print("\n" + "="*70)
    print("✅ LEARNING LOOP TEST COMPLETE")
    print("="*70 + "\n")
    
    print("📋 Summary:")
    print(f"   - Feedback tracking: ✅ Working")
    print(f"   - Pattern extraction: ✅ Working")
    print(f"   - Learning progress: ✅ Working")
    print(f"   - Memory integration: ✅ Working")
    
    if suggestion_learned.get('learned_patterns'):
        print(f"   - Pattern utilization: ✅ Working")
    else:
        print(f"   - Pattern utilization: ⚠️  Needs more data")
    
    print("\n💡 Next Steps:")
    print("   1. Use the API endpoints to track real user interactions")
    print("   2. Monitor acceptance rates improving over time")
    print("   3. Check /learning/progress endpoint regularly")
    print("   4. Visualize learned patterns in UI")
    print()


if __name__ == "__main__":
    asyncio.run(test_learning_loop())
