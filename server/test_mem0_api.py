#!/usr/bin/env python3
"""
Test script to verify Mem0 API usage
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    env_path = script_dir / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from {env_path}")
        print(f"🔑 OPENAI_API_KEY: {'configured' if os.getenv('OPENAI_API_KEY') else 'missing'}")
    else:
        print(f"⚠️  .env file not found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, .env file not loaded")

try:
    from mem0 import Memory
    print("✅ Mem0 import successful")

    # Test Memory initialization
    memory = Memory()
    print("✅ Memory initialization successful")

    # Test the add method signature
    try:
        # Try the simple positional argument approach
        memory.add("test content", user_id="test_user", metadata={"test": True})
        print("✅ Memory.add() with positional argument works")
    except Exception as e:
        print(f"❌ Memory.add() with positional argument failed: {e}")

        # Try with keyword argument
        try:
            memory.add(memory="test content", user_id="test_user", metadata={"test": True})
            print("✅ Memory.add() with memory= keyword works")
        except Exception as e2:
            print(f"❌ Memory.add() with memory= keyword failed: {e2}")

    # Test search
    try:
        results = memory.search(query="test", user_id="test_user")
        print(f"✅ Memory.search() works, returned {len(results) if results else 0} results")
    except Exception as e:
        print(f"❌ Memory.search() failed: {e}")

except ImportError as e:
    print(f"❌ Failed to import Mem0: {e}")
except Exception as e:
    print(f"❌ Error testing Mem0: {e}")
