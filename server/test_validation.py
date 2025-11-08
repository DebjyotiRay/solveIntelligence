"""
Test the replacement validation logic
"""

from app.ai.agents.structure_agent import DocumentStructureAgent

agent = DocumentStructureAgent()

# Test cases
test_cases = [
    {
        "target": "is transparent and lightweight.",
        "replacement": "is transparent and lightweight. is transparent and lightweight.",
        "should_pass": False,
        "reason": "Duplicate text"
    },
    {
        "target": "lightweight",
        "replacement": "lightweight.",
        "should_pass": True,
        "reason": "Valid - adds period"
    },
    {
        "target": "recieve",
        "replacement": "receive",
        "should_pass": True,
        "reason": "Valid - spelling fix"
    },
    {
        "target": "device",
        "replacement": "device",
        "should_pass": False,
        "reason": "Identical"
    },
    {
        "target": "test",
        "replacement": "test test test",
        "should_pass": False,
        "reason": "Contains target 3 times"
    }
]

print("\n" + "="*80)
print("TESTING REPLACEMENT VALIDATION")
print("="*80)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    result = agent._is_valid_replacement(test['target'], test['replacement'])
    expected = test['should_pass']

    status = "✅ PASS" if result == expected else "❌ FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1

    print(f"\n{i}. {status}")
    print(f"   Target: '{test['target']}'")
    print(f"   Replacement: '{test['replacement']}'")
    print(f"   Reason: {test['reason']}")
    print(f"   Expected: {expected}, Got: {result}")

print("\n" + "="*80)
print(f"Results: {passed} passed, {failed} failed")
print("="*80)
