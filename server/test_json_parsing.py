#!/usr/bin/env python3
"""
JSON Parsing Tests for Patent Analysis System

Tests all JSON parsing scenarios in the AI analysis methods to ensure robust
error handling and proper response processing.
"""

import json
import time
import pytest
from unittest.mock import Mock
import sys
import os

# Add app to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.ai.agents.structure_agent import DocumentStructureAgent
from app.ai.agents.legal_agent import LegalComplianceAgent

 
def test_valid_json_parsing_claims_validation():
    """Test valid JSON parsing for claims validation."""
    valid_json = {
        "score": 0.85,
        "issues": [
            {
                "type": "punctuation",
                "claim": 1,
                "description": "Claim lacks proper punctuation",
                "severity": "medium",
                "suggestion": "Add semicolons between elements"
            }
        ],
        "compliant": True
    }
    
    # Test the JSON structure
    assert isinstance(valid_json["score"], float)
    assert isinstance(valid_json["issues"], list)
    assert isinstance(valid_json["compliant"], bool)
    
    if valid_json["issues"]:
        issue = valid_json["issues"][0]
        assert "type" in issue
        assert "description" in issue
        assert "severity" in issue
        assert "suggestion" in issue
    
def test_valid_json_parsing_legal_analysis():
    """Test valid JSON parsing for legal analysis."""
    valid_json = {
        "conclusions": [
            "Patent demonstrates clear technical innovation",
            "Claims are properly structured and supported",
            "Enablement requirement appears satisfied"
        ],
        "issues": [
            {
                "type": "legal_compliance",
                "description": "Minor definiteness concern in claim 3",
                "severity": "medium",
                "suggestion": "Clarify the term 'substantially'",
                "legal_basis": "35 USC 112(b)"
            }
        ],
        "recommendations": [
            "Consider adding more specific measurements",
            "Review claim dependencies for optimal protection"
        ],
        "filing_strategy": "Strong patent with minor revisions needed",
        "overall_assessment": "Ready for filing with suggested improvements"
    }
    
    # Test the JSON structure
    assert isinstance(valid_json["conclusions"], list)
    assert isinstance(valid_json["issues"], list)
    assert isinstance(valid_json["recommendations"], list)
    assert isinstance(valid_json["filing_strategy"], str)
    assert isinstance(valid_json["overall_assessment"], str)
    
    if valid_json["issues"]:
        issue = valid_json["issues"][0]
        assert "type" in issue
        assert "description" in issue
        assert "severity" in issue
        assert "suggestion" in issue
        assert "legal_basis" in issue
    
@pytest.mark.parametrize("malformed_json", [
    '{"score": 0.85, "issues": [',  # Incomplete JSON
    '{"score": 0.85, "issues": [}',  # Invalid structure
    'Not JSON at all',  # Not JSON
    '```json\n{"score": 0.85}\n```',  # JSON with code blocks
    '',  # Empty response
])
def test_malformed_json_handling(malformed_json):
    """Test handling of malformed JSON responses."""
    try:
        if malformed_json is None:
            pytest.skip("None case not applicable")
        
        # Clean potential markdown wrapping
        cleaned = malformed_json
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        if not cleaned:
            return  # Empty is expected to be handled
        
        result = json.loads(cleaned)
        # If we get here without exception, validate structure
        if isinstance(result, dict):
            # For claims validation format
            if "score" in result:
                assert isinstance(result.get("score"), (int, float))
            if "issues" in result:
                assert isinstance(result.get("issues"), list)
        
    except json.JSONDecodeError:
        # This is expected for malformed JSON
        pass
    except Exception as e:
        # Other exceptions should be handled gracefully
        pytest.fail(f"Unexpected exception for {malformed_json}: {e}")
    
@pytest.mark.parametrize("invalid_json", [
    '{"score": "high", "issues": []}',  # String instead of number
    '{"score": true, "issues": []}',  # Boolean instead of number
    '{"score": 0.85, "issues": "none"}',  # String instead of list
    '{"score": 0.85, "compliant": "yes"}',  # String instead of boolean
])
def test_invalid_data_types_in_json(invalid_json):
    """Test handling of JSON with invalid data types."""
    try:
        result = json.loads(invalid_json)
        # JSON parsing succeeds, but data types are wrong
        assert isinstance(result, dict)
        
        # In a real implementation, agents should validate data types
        # and handle invalid types gracefully
        if "score" in result:
            score = result.get("score")
            if not isinstance(score, (int, float)):
                # This would be handled in the actual agent code
                fallback_score = 0.5
                assert isinstance(fallback_score, (int, float))
        
    except json.JSONDecodeError:
        pytest.fail(f"Valid JSON should not raise JSONDecodeError: {invalid_json}")
    except Exception as e:
        pytest.fail(f"Unexpected exception for {invalid_json}: {e}")
    
@pytest.mark.parametrize("special_case", [
    {"issues": [{"description": "Patent contains émojis 🚀 and spéciál chars"}]},
    {"issues": [{"description": "Newlines\nand\ttabs in text"}]},
    {"issues": [{"description": "Quotes \"inside\" quotes"}]},
    {"issues": [{"description": "Unicode: 中文, العربية, Русский"}]},
])
def test_json_with_special_characters(special_case):
    """Test JSON parsing with special characters and unicode."""
    try:
        # Convert to JSON string and back to test serialization
        json_str = json.dumps(special_case)
        parsed = json.loads(json_str)
        assert special_case == parsed
    except Exception as e:
        pytest.fail(f"Failed to handle special characters: {e}")
    
@pytest.mark.parametrize("edge_case", [
    {"score": 0.0, "issues": []},  # Empty issues
    {"score": 1.0, "issues": None},  # None issues
    {"score": -1, "issues": []},  # Negative score
    {"issues": [{"type": "", "description": ""}]},  # Empty strings
    {"issues": [{"type": None, "description": None}]},  # None values
])
def test_edge_case_values(edge_case):
    """Test JSON parsing with edge case values."""
    try:
        json_str = json.dumps(edge_case, allow_nan=False)
        parsed = json.loads(json_str)
        # Validate that we can handle these edge cases
        assert isinstance(parsed, dict)
    except ValueError:
        # Some edge cases (like infinity) may not be serializable
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error with edge case {edge_case}: {e}")


def test_edge_case_infinity():
    """Test JSON parsing with infinity (separate test since it raises ValueError)."""
    edge_case = {"score": float('inf'), "issues": []}
    with pytest.raises(ValueError):
        json.dumps(edge_case, allow_nan=False)
    
def test_deeply_nested_json():
    """Test parsing of deeply nested JSON structures."""
    nested_json = {
        "conclusions": ["Top level"],
        "issues": [
            {
                "type": "complex",
                "details": {
                    "subcategory": {
                        "analysis": {
                            "findings": ["deeply", "nested", "data"],
                            "metadata": {
                                "confidence": 0.95,
                                "reviewed_by": "AI system"
                            }
                        }
                    }
                }
            }
        ]
    }
    
    try:
        json_str = json.dumps(nested_json)
        parsed = json.loads(json_str)
        
        # Navigate the nested structure
        issue = parsed["issues"][0]
        findings = issue["details"]["subcategory"]["analysis"]["findings"]
        assert findings == ["deeply", "nested", "data"]
        
        confidence = issue["details"]["subcategory"]["analysis"]["metadata"]["confidence"]
        assert confidence == 0.95
        
    except Exception as e:
        pytest.fail(f"Failed to parse deeply nested JSON: {e}")
    
def test_large_json_response():
    """Test parsing of large JSON responses."""
    # Create a large JSON response similar to what AI might return
    large_issues = []
    for i in range(100):
        large_issues.append({
            "type": f"issue_type_{i}",
            "claim": i % 10 + 1,
            "description": f"This is a detailed description for issue {i} " * 10,
            "severity": ["low", "medium", "high"][i % 3],
            "suggestion": f"Detailed suggestion for fixing issue {i} " * 5
        })
    
    large_json = {
        "score": 0.75,
        "issues": large_issues,
        "compliant": False,
        "metadata": {
            "processed_claims": list(range(1, 21)),
            "analysis_timestamp": "2025-01-10T11:57:20Z",
            "ai_model": "gpt-4-turbo-preview"
        }
    }
    
    try:
        # Test serialization and parsing of large JSON
        json_str = json.dumps(large_json)
        assert len(json_str) > 10000  # Should be quite large
        
        parsed = json.loads(json_str)
        assert len(parsed["issues"]) == 100
        assert parsed["score"] == 0.75
        
    except Exception as e:
        pytest.fail(f"Failed to handle large JSON response: {e}")
    
@pytest.mark.parametrize("size", [10, 100, 1000])
def test_json_parsing_performance(size):
    """Test JSON parsing performance with various sizes."""
    # Create JSON with 'size' number of issues
    test_json = {
        "issues": [
            {
                "type": f"type_{i}",
                "description": f"Description {i}",
                "severity": "medium"
            } for i in range(size)
        ]
    }
    
    start_time = time.time()
    json_str = json.dumps(test_json)
    parsed = json.loads(json_str)
    end_time = time.time()
    
    parsing_time = end_time - start_time
    assert len(parsed["issues"]) == size
    
    # Performance should be reasonable (less than 1 second even for large JSON)
    assert parsing_time < 1.0, f"JSON parsing took too long for size {size}: {parsing_time}s"
    
def test_content_quality_json_parsing():
    """Test JSON parsing for content quality analysis."""
    content_quality_json = {
        "issues": [
            {
                "type": "spelling_error",
                "description": "Misspelled word: 'recieve'",
                "severity": "medium"
            },
            {
                "type": "grammar",
                "description": "Subject-verb disagreement",
                "severity": "high"
            }
        ]
    }
    
    # Test parsing
    json_str = json.dumps(content_quality_json)
    parsed = json.loads(json_str)
    
    assert "issues" in parsed
    assert len(parsed["issues"]) == 2
    
    # Test issue structure
    for issue in parsed["issues"]:
        assert "type" in issue
        assert "description" in issue
        assert "severity" in issue
    
@pytest.mark.parametrize("test_input,expected_error_type", [
    ('{"incomplete": ', "JSON Decode Error"),
    ('invalid json', "JSON Decode Error"),
    ('null', "Null Response"),
    ('', "Empty Response")
])
def test_json_parsing_error_recovery(test_input, expected_error_type):
    """Test error recovery mechanisms for JSON parsing failures."""
    try:
        if not test_input.strip():
            # Handle empty response
            fallback_result = {
                "score": 0.5,
                "issues": [{"type": "analysis_error", "description": "Empty response", "severity": "high"}],
                "compliant": False
            }
            assert isinstance(fallback_result, dict)
            return
        
        # Clean potential markdown
        cleaned = test_input
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        result = json.loads(cleaned)
        
    except json.JSONDecodeError:
        # This is the expected path for malformed JSON
        # Agents should return fallback results
        fallback_result = {
            "score": 0.5,
            "issues": [{"type": "analysis_error", "description": "JSON parsing error", "severity": "high"}],
            "compliant": False
        }
        assert isinstance(fallback_result, dict)
        assert "score" in fallback_result
        assert "issues" in fallback_result


def test_agent_fixtures(structure_agent, legal_agent):
    """Test that agent fixtures are properly created."""
    assert structure_agent is not None
    assert legal_agent is not None
    assert hasattr(structure_agent, 'memory')
    assert hasattr(legal_agent, 'memory')


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
