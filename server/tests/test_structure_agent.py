"""
Tests for Structure Agent
"""
import pytest
from app.ai.agents.structure_agent import DocumentStructureAgent
from app.ai.types import StructureAnalysisResult, StructuralIssue


def test_agent_instantiation():
    """Test that structure agent can be instantiated"""
    agent = DocumentStructureAgent()
    assert agent.agent_name == "structure"


def test_extract_title():
    """Test title extraction"""
    agent = DocumentStructureAgent()
    content = """
    Wireless Optogenetic Device Patent
    
    ABSTRACT
    This is the abstract...
    """
    title = agent._extract_title(content)
    assert "Wireless" in title or "Patent" in title


def test_extract_claims():
    """Test claims extraction"""
    agent = DocumentStructureAgent()
    content = """
    CLAIMS
    
    1. A device comprising a first element and a second element.
    
    2. The device of claim 1, wherein the first element is wireless.
    
    3. The device of claim 1, wherein the second element provides power.
    """
    claims = agent._extract_claims(content)
    assert len(claims) >= 2
    assert claims[0]["number"] == 1
    assert "device" in claims[0]["text"].lower()


def test_parse_document_sections():
    """Test document section parsing"""
    agent = DocumentStructureAgent()
    content = """
    Test Patent Title
    
    ABSTRACT
    This invention relates to a novel device.
    
    BACKGROUND
    Prior art devices have limitations.
    
    CLAIMS
    1. A device comprising elements.
    """
    parsed = agent._parse_document_sections(content)
    
    assert isinstance(parsed, dict)
    assert "title" in parsed
    assert "claims" in parsed
    assert "word_count" in parsed
    assert parsed["word_count"] > 0


@pytest.mark.asyncio
async def test_ai_validate_returns_typed_result():
    """Test that AI validation returns properly typed result"""
    agent = DocumentStructureAgent()
    
    # Mock parsed document
    parsed_doc = {
        "title": "Test Patent",
        "abstract": "Test abstract content",
        "claims": [{"number": 1, "text": "A device"}],
        "full_text": "Test content"
    }
    
    # This will return error if no API key, but should still be typed
    result = await agent._ai_validate_document(parsed_doc)
    
    # Verify it's a StructureAnalysisResult instance
    assert isinstance(result, StructureAnalysisResult)
    assert hasattr(result, 'status')
    assert hasattr(result, 'confidence')
    assert hasattr(result, 'issues')
    assert hasattr(result, 'suggestions')
    assert result.status in ["complete", "error"]
    assert 0.0 <= result.confidence <= 1.0
