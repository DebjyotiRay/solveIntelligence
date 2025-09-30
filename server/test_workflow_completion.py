#!/usr/bin/env python3
"""
Test script to verify complete workflow execution without websocket
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

async def test_complete_workflow():
    """Test the complete workflow execution"""
    try:
        from ai.workflow.patent_coordinator import PatentAnalysisCoordinator
        print("✅ PatentAnalysisCoordinator import successful")

        # Initialize coordinator
        coordinator = PatentAnalysisCoordinator()
        print("✅ PatentAnalysisCoordinator initialization successful")

        # Create test document
        test_document = {
            "id": "test_workflow_doc",
            "content": "<html><body><h1>Wireless Optogenetic Device Patent</h1><p>Test patent content for workflow testing...</p></body></html>",
            "clean_text": "Wireless Optogenetic Device Patent. Test patent content for workflow testing...",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        print(f"🧪 Testing complete workflow execution...")

        # Simple callback to track progress
        async def test_callback(update):
            print(f"📢 WORKFLOW UPDATE: {update.get('phase', 'unknown')} - {update.get('message', 'no message')}")

        # Execute the workflow
        result = await coordinator.analyze_patent(test_document, test_callback)

        print(f"🎉 Workflow completed!")
        print(f"📊 Result keys: {list(result.keys()) if result else 'None'}")
        print(f"📊 Status: {result.get('status') if result else 'None'}")
        print(f"📊 Final analysis present: {result.get('final_analysis') is not None if result else 'None'}")

        # The result IS the final analysis! Let's check this
        print(f"📊 Result is the final analysis itself!")
        print(f"📊 Overall score: {result.get('overall_score') if result else 'None'}")
        print(f"📊 Analysis timestamp: {result.get('analysis_timestamp') if result else 'None'}")

        return result

    except Exception as e:
        print(f"❌ Error testing workflow: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_complete_workflow())