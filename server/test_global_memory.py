#!/usr/bin/env python3
"""
Test script to isolate global memory storage issue
"""

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

try:
    from ai.memory.patent_memory import PatentAnalysisMemory
    print("✅ PatentAnalysisMemory import successful")

    # Test Memory initialization
    memory = PatentAnalysisMemory()
    print("✅ PatentAnalysisMemory initialization successful")

    # Test global memory storage specifically
    print(f"\\n🧪 Testing global memory storage...")

    test_analysis = {
        "document_id": "test_global_doc",
        "overall_score": 0.75,
        "patent_type": "device",
        "domain": "medical",
        "all_issues": [{"type": "test", "description": "Test issue"}],
        "analysis_metadata": {
            "agents_used": ["structure", "legal"],
            "workflow_version": "3.0"
        }
    }

    success = memory.store_analysis_summary("test_global_doc", test_analysis)
    if success:
        print("✅ Global memory storage successful")
    else:
        print("❌ Global memory storage failed")

    # Try to retrieve from global memory
    print(f"\\n🧪 Testing global memory retrieval...")
    try:
        all_results = memory.memory.get_all()
        global_results = [r for r in all_results if r.get('user_id') == 'global_memory']
        print(f"🔍 Found {len(global_results)} global memory entries")

        for i, result in enumerate(global_results):
            metadata = result.get('metadata', {})
            analysis_type = metadata.get('type', 'unknown')
            score = metadata.get('overall_score', 'N/A')
            print(f"   Entry {i+1}: type={analysis_type}, score={score}")
    except Exception as e:
        print(f"❌ Failed to retrieve global memories: {e}")

except ImportError as e:
    print(f"❌ Failed to import PatentAnalysisMemory: {e}")
except Exception as e:
    print(f"❌ Error testing global memory: {e}")
    import traceback
    traceback.print_exc()