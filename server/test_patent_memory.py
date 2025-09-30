#!/usr/bin/env python3
"""
Test script to verify PatentAnalysisMemory implementation
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

    # Test storing agent findings
    test_document_id = "test_doc_123"
    test_agent = "structure"
    test_findings = {
        "confidence": 0.85,
        "issues": [
            {"type": "format", "description": "Missing section"},
            {"type": "clarity", "description": "Unclear claim"}
        ],
        "recommendations": ["Add abstract", "Clarify claims"],
        "type": "structure_analysis"
    }

    print(f"\n🧪 Testing agent findings storage...")
    success = memory.store_agent_findings(test_document_id, test_agent, test_findings)
    if success:
        print("✅ Agent findings stored successfully")
    else:
        print("❌ Failed to store agent findings")

    # Test retrieving shared context
    print(f"\n🧪 Testing shared context retrieval...")
    context = memory.get_shared_analysis_context(test_document_id)
    print(f"📚 Retrieved context: {len(context.get('agent_findings', {}))} agent findings")

    if context.get('agent_findings') and test_agent in context['agent_findings']:
        stored_findings = context['agent_findings'][test_agent]
        print(f"✅ Found stored findings for {test_agent}")
        print(f"   - Confidence: {stored_findings.get('confidence')}")
        print(f"   - Issues: {len(stored_findings.get('issues', []))}")
        print(f"   - Type: {stored_findings.get('type')}")
    else:
        print("❌ Could not retrieve stored findings")

    # Test storing a second agent's findings
    print(f"\n🧪 Testing second agent findings...")
    legal_findings = {
        "confidence": 0.75,
        "compliance_score": 0.8,
        "issues": [
            {"type": "legal", "description": "Prior art concern"},
        ],
        "recommendations": ["Review prior art"],
        "type": "legal_analysis"
    }

    # Add small delay to avoid API rate limits
    import time
    time.sleep(1)

    success = memory.store_agent_findings(test_document_id, "legal", legal_findings)
    if success:
        print("✅ Legal agent findings stored successfully")

        # Test cross-agent insights
        context = memory.get_shared_analysis_context(test_document_id)
        agent_findings = context.get('agent_findings', {})
        print(f"📚 Now have {len(agent_findings)} agents in context: {list(agent_findings.keys())}")

        # Test cross-agent insight generation
        if len(agent_findings) >= 2:
            print("✅ Multiple agents detected - cross-agent insights possible")
            print(f"   - Structure confidence: {agent_findings.get('structure', {}).get('confidence')}")
            print(f"   - Legal confidence: {agent_findings.get('legal', {}).get('confidence')}")
        else:
            print("❌ Not enough agents for cross-agent insights")

    # Test workflow progress storage
    print(f"\n🧪 Testing workflow progress...")
    progress_data = {
        "message": "Test workflow phase completed",
        "agents_completed": ["structure", "legal"],
        "phase": "test_phase"
    }

    success = memory.store_workflow_progress(test_document_id, "test_phase", progress_data)
    if success:
        print("✅ Workflow progress stored successfully")
    else:
        print("❌ Failed to store workflow progress")

    print(f"\n🎉 All tests completed!")

except ImportError as e:
    print(f"❌ Failed to import PatentAnalysisMemory: {e}")
    print("Make sure you're running from the server directory")
except Exception as e:
    print(f"❌ Error testing PatentAnalysisMemory: {e}")
    import traceback
    traceback.print_exc()