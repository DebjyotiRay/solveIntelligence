#!/usr/bin/env python3
"""
Test script to run two sequential analyses and see if the second finds the first
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
script_dir = Path(__file__).parent
app_dir = script_dir / "app"
sys.path.insert(0, str(app_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = script_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from {env_path}")
    else:
        print(f"⚠️  .env file not found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available")

async def test_sequential_analyses():
    """Test running two analyses to see if global memory works"""
    try:
        from ai.workflow.patent_coordinator import PatentAnalysisCoordinator
        print("✅ PatentAnalysisCoordinator import successful")

        # Initialize coordinator
        coordinator = PatentAnalysisCoordinator()
        print("✅ PatentAnalysisCoordinator initialization successful")

        # Create first test document
        test_document1 = {
            "id": "sequential_test_doc_1",
            "content": "<html><body><h1>Medical Device Patent</h1><p>A revolutionary medical device for patient monitoring...</p></body></html>",
            "clean_text": "Medical Device Patent. A revolutionary medical device for patient monitoring...",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        print(f"🧪 Running FIRST analysis...")

        # Simple callback to track progress
        async def test_callback(update):
            print(f"📢 ANALYSIS 1: {update.get('phase', 'unknown')} - {update.get('message', 'no message')}")

        # Execute the first workflow
        result1 = await coordinator.analyze_patent(test_document1, test_callback)
        print(f"🎉 First analysis completed! Score: {result1.get('overall_score', 'N/A')}")

        # Now create second test document with similar characteristics
        test_document2 = {
            "id": "sequential_test_doc_2",
            "content": "<html><body><h1>Another Medical Device Patent</h1><p>Another innovative medical device for healthcare...</p></body></html>",
            "clean_text": "Another Medical Device Patent. Another innovative medical device for healthcare...",
            "timestamp": "2024-01-02T00:00:00Z"
        }

        print(f"\\n🧪 Running SECOND analysis (should find first as similar case)...")

        async def test_callback2(update):
            print(f"📢 ANALYSIS 2: {update.get('phase', 'unknown')} - {update.get('message', 'no message')}")

        # Execute the second workflow
        result2 = await coordinator.analyze_patent(test_document2, test_callback2)
        print(f"🎉 Second analysis completed! Score: {result2.get('overall_score', 'N/A')}")

        # Check if the second analysis found the first as a similar case
        similar_cases_found = len(result2.get('similar_cases', []))
        print(f"📊 Similar cases found by second analysis: {similar_cases_found}")

        if similar_cases_found > 0:
            print("✅ SUCCESS: Global memory is working - second analysis found previous case!")
        else:
            print("❌ ISSUE: Second analysis didn't find first as similar case")

        return result1, result2

    except Exception as e:
        print(f"❌ Error testing sequential analyses: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    result1, result2 = asyncio.run(test_sequential_analyses())