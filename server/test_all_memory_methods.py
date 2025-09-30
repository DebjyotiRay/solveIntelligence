#!/usr/bin/env python3
"""
Comprehensive test script to verify all PatentAnalysisMemory methods work with updated API
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

    test_document_id = "comprehensive_test_doc"

    print(f"\n🧪 === COMPREHENSIVE MEMORY SYSTEM TEST ===")

    # 1. Test agent findings storage and retrieval
    print(f"\n1️⃣ Testing agent findings storage and cross-agent context...")

    structure_findings = {
        "confidence": 0.82,
        "issues": [{"type": "format", "description": "Missing abstract"}],
        "recommendations": ["Add comprehensive abstract"],
        "type": "structure_analysis"
    }

    legal_findings = {
        "confidence": 0.78,
        "compliance_score": 0.8,
        "issues": [{"type": "legal", "description": "Prior art concern"}],
        "recommendations": ["Review prior art thoroughly"],
        "type": "legal_analysis"
    }

    # Store findings
    success1 = memory.store_agent_findings(test_document_id, "structure", structure_findings)
    success2 = memory.store_agent_findings(test_document_id, "legal", legal_findings)

    if success1 and success2:
        print("✅ Both agent findings stored successfully")
    else:
        print("❌ Failed to store agent findings")

    # Retrieve shared context
    context = memory.get_shared_analysis_context(test_document_id)
    agent_count = len(context.get('agent_findings', {}))
    print(f"📚 Retrieved context with {agent_count} agent findings")

    if agent_count >= 2:
        print("✅ Cross-agent context working correctly")
        agents = list(context['agent_findings'].keys())
        for agent in agents:
            findings = context['agent_findings'][agent]
            print(f"   - {agent}: confidence={findings.get('confidence')}, issues={len(findings.get('issues', []))}")
    else:
        print("❌ Cross-agent context not working")

    # 2. Test workflow progress tracking
    print(f"\n2️⃣ Testing workflow progress tracking...")

    progress_data = {
        "message": "Cross-validation phase completed",
        "conflicts_found": 1,
        "resolutions_applied": 1
    }

    success = memory.store_workflow_progress(test_document_id, "cross_validation", progress_data)
    if success:
        print("✅ Workflow progress stored successfully")
    else:
        print("❌ Failed to store workflow progress")

    # Get workflow progress
    progress = memory.get_workflow_progress(test_document_id)
    completed_agents = progress.get('completed_agents', [])
    print(f"📊 Workflow progress: {len(completed_agents)} completed agents: {completed_agents}")
    print(f"   - Current phase: {progress.get('current_phase')}")
    print(f"   - Total issues: {progress.get('total_issues')}")
    print(f"   - Overall confidence: {progress.get('overall_confidence', 0):.2f}")

    # 3. Test cross-agent insights
    print(f"\n3️⃣ Testing cross-agent insights...")

    insight = {
        "type": "confidence_divergence",
        "description": "Structure and legal agents show confidence gap",
        "agents": ["structure", "legal"],
        "confidence": 0.8
    }

    success = memory.store_cross_agent_insight(test_document_id, insight)
    if success:
        print("✅ Cross-agent insight stored successfully")
    else:
        print("❌ Failed to store cross-agent insight")

    # 4. Test analysis summary storage
    print(f"\n4️⃣ Testing analysis summary storage...")

    analysis_summary = {
        "document_id": test_document_id,
        "overall_score": 0.80,
        "patent_type": "device",
        "domain": "medical",
        "all_issues": structure_findings["issues"] + legal_findings["issues"],
        "analysis_metadata": {
            "agents_used": ["structure", "legal"],
            "workflow_version": "3.0"
        }
    }

    success = memory.store_analysis_summary(test_document_id, analysis_summary)
    if success:
        print("✅ Analysis summary stored successfully")
    else:
        print("❌ Failed to store analysis summary")

    # 5. Test similar cases retrieval
    print(f"\n5️⃣ Testing similar cases retrieval...")

    document_characteristics = {
        "domain": "medical",
        "patent_type": "device"
    }

    similar_cases = memory.get_similar_cases(document_characteristics)
    print(f"🔍 Found {len(similar_cases)} similar cases")

    if similar_cases:
        print("✅ Similar cases retrieval working")
        for i, case in enumerate(similar_cases[:2]):  # Show first 2
            print(f"   - Case {i+1}: score={case.get('overall_score', 'N/A')}")
    else:
        print("⚠️  No similar cases found (expected for first run)")

    # 6. Test correction patterns
    print(f"\n6️⃣ Testing correction patterns...")

    correction_pattern = {
        "type": "confidence_adjustment",
        "description": "Adjust confidence for medical device patents",
        "effectiveness": 0.85
    }

    success = memory.store_correction_pattern("structure", correction_pattern)
    if success:
        print("✅ Correction pattern stored successfully")
    else:
        print("❌ Failed to store correction pattern")

    # Retrieve correction patterns
    patterns = memory.get_agent_correction_patterns("structure")
    print(f"🔧 Found {len(patterns)} correction patterns for structure agent")

    if patterns:
        print("✅ Correction patterns retrieval working")
        for i, pattern in enumerate(patterns[:2]):  # Show first 2
            print(f"   - Pattern {i+1}: type={pattern.get('type')}, effectiveness={pattern.get('effectiveness')}")

    # 7. Test memory stats
    print(f"\n7️⃣ Testing memory system stats...")

    stats = memory.get_memory_stats()
    print(f"📈 Memory stats: {stats.get('status')}")

    if stats.get('status') == 'active':
        print("✅ Memory system operational")
    else:
        print(f"⚠️  Memory system status: {stats}")

    print(f"\n🎉 === COMPREHENSIVE TEST COMPLETED ===")
    print(f"📊 Summary:")
    print(f"   - Agent findings: {'✅' if agent_count >= 2 else '❌'}")
    print(f"   - Workflow progress: {'✅' if len(completed_agents) >= 2 else '❌'}")
    print(f"   - Cross-agent insights: {'✅' if success else '❌'}")
    print(f"   - Analysis summary: {'✅' if success else '❌'}")
    print(f"   - Similar cases: {'✅' if similar_cases else '⚠️'}")
    print(f"   - Correction patterns: {'✅' if patterns else '⚠️'}")
    print(f"   - Memory stats: {'✅' if stats.get('status') == 'active' else '❌'}")

except ImportError as e:
    print(f"❌ Failed to import PatentAnalysisMemory: {e}")
except Exception as e:
    print(f"❌ Error testing PatentAnalysisMemory: {e}")
    import traceback
    traceback.print_exc()