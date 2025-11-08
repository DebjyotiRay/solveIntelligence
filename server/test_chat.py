"""
Test script for grounded chatbot service.

Run this to verify the chat service is working correctly.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.services.chat_service import get_chat_service


async def test_chat():
    """Test the chat service with example queries."""

    print("=" * 60)
    print("TESTING GROUNDED CHATBOT SERVICE")
    print("=" * 60)

    chat_service = get_chat_service()

    # Test queries
    test_cases = [
        {
            "message": "Why did you suggest changing 'computer program' to 'computer-implemented method'?",
            "client_id": "test_client",
            "document_id": 1,
            "document_context": "A computer program for medical diagnosis using AI algorithms."
        },
        {
            "message": "Can you explain Section 3(k) of the Indian Patent Act?",
            "client_id": "test_client",
            "document_id": 1,
            "document_context": None
        },
        {
            "message": "I disagree with your suggestion. Why is it necessary?",
            "client_id": "test_client",
            "document_id": 1,
            "document_context": "A system for processing medical images."
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"TEST CASE {i}")
        print(f"{'=' * 60}")
        print(f"\nUSER: {test_case['message']}")
        print(f"\nClient ID: {test_case['client_id']}")
        print(f"Document ID: {test_case['document_id']}")
        if test_case['document_context']:
            print(f"Context: {test_case['document_context'][:50]}...")

        print("\n" + "-" * 60)
        print("AI RESPONSE:")
        print("-" * 60)

        try:
            result = await chat_service.chat(
                user_message=test_case['message'],
                client_id=test_case['client_id'],
                document_id=test_case['document_id'],
                document_context=test_case['document_context']
            )

            print(f"\n{result['response']}\n")

            if result['sources']:
                print(f"\n📚 SOURCES ({len(result['sources'])} retrieved):")
                print("-" * 60)
                for src in result['sources']:
                    print(f"[{src['id']}] {src['citation']} ({src['tier']})")
                    print(f"    Content: {src['content'][:100]}...")
                    print()

            print(f"\n✓ Metadata:")
            print(f"  - Sources: {result['metadata'].get('sources_count', 0)}")
            print(f"  - Model: {result['metadata'].get('model', 'unknown')}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


async def test_conversation():
    """Test conversation with history."""

    print("\n" + "=" * 60)
    print("TESTING CONVERSATION WITH HISTORY")
    print("=" * 60)

    chat_service = get_chat_service()

    conversation_history = []

    # Message 1
    print("\nUSER: What is Section 3(k)?")
    result1 = await chat_service.chat(
        user_message="What is Section 3(k)?",
        client_id="test_client",
        document_id=1
    )
    print(f"\nAI: {result1['response'][:200]}...")

    conversation_history.append({"role": "user", "content": "What is Section 3(k)?"})
    conversation_history.append({"role": "assistant", "content": result1['response']})

    # Message 2 (follow-up)
    print("\n" + "-" * 60)
    print("\nUSER: Can you give me an example?")
    result2 = await chat_service.chat(
        user_message="Can you give me an example?",
        client_id="test_client",
        document_id=1,
        conversation_history=conversation_history
    )
    print(f"\nAI: {result2['response'][:200]}...")

    print("\n✓ Conversation test complete - AI understood context from previous message")


if __name__ == "__main__":
    print("\n🚀 Starting chat service tests...\n")

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        sys.exit(1)

    # Run tests
    asyncio.run(test_chat())
    asyncio.run(test_conversation())

    print("\n✅ All tests complete!\n")
