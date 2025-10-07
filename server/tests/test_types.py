"""
Tests for Pydantic type models
"""
import pytest
from pydantic import ValidationError
from app.ai.types import (
    StructuralIssue, 
    StructureAnalysisResult,
    LegalIssue,
    LegalAnalysisResult,
    AgentAnalysisState
)


def test_structural_issue_validation():
    """Test StructuralIssue model validation"""
    issue = StructuralIssue(
        type="missing_section",
        severity="high",
        description="Missing abstract section",
        suggestion="Add abstract section"
    )
    
    assert issue.type == "missing_section"
    assert issue.severity == "high"
    assert issue.location is None


def test_structural_issue_invalid_severity():
    """Test that invalid severity raises validation error"""
    with pytest.raises(ValidationError):
        StructuralIssue(
            type="format_error",
            severity="critical",  # Invalid - must be high/medium/low
            description="Test",
            suggestion="Fix it"
        )


def test_structure_analysis_result_valid():
    """Test StructureAnalysisResult creation"""
    result = StructureAnalysisResult(
        status="complete",
        confidence=0.85,
        issues=[
            StructuralIssue(
                type="clarity_issue",
                severity="medium",
                description="Vague language",
                suggestion="Be more specific"
            )
        ],
        suggestions=["Suggestion 1", "Suggestion 2"]
    )
    
    assert result.status == "complete"
    assert result.confidence == 0.85
    assert len(result.issues) == 1
    assert len(result.suggestions) == 2


def test_structure_analysis_result_confidence_validation():
    """Test confidence score must be between 0 and 1"""
    with pytest.raises(ValidationError):
        StructureAnalysisResult(
            status="complete",
            confidence=1.5,  # Invalid - must be <= 1.0
            issues=[],
            suggestions=[]
        )
    
    with pytest.raises(ValidationError):
        StructureAnalysisResult(
            status="complete",
            confidence=-0.1,  # Invalid - must be >= 0.0
            issues=[],
            suggestions=[]
        )


def test_structure_analysis_result_defaults():
    """Test default values for optional fields"""
    result = StructureAnalysisResult(status="complete")
    
    assert result.confidence == 0.0
    assert result.issues == []
    assert result.suggestions == []
    assert result.sections == []
    assert result.claims == []


def test_legal_issue_validation():
    """Test LegalIssue model"""
    issue = LegalIssue(
        type="prior_art",
        severity="high",
        description="Similar patent exists",
        suggestion="Differentiate claims",
        legal_basis="35 U.S.C. § 102"
    )
    
    assert issue.type == "prior_art"
    assert issue.legal_basis == "35 U.S.C. § 102"


def test_legal_analysis_result():
    """Test LegalAnalysisResult model"""
    result = LegalAnalysisResult(
        issues=[
            LegalIssue(
                type="compliance",
                severity="medium",
                description="Missing required disclosure",
                suggestion="Add disclosure section"
            )
        ],
        confidence=0.75,
        recommendations=["Review disclosure requirements"],
        conclusions=["Overall assessment positive"]
    )
    
    assert result.type == "legal_analysis"
    assert result.confidence == 0.75
    assert len(result.issues) == 1
    assert len(result.recommendations) == 1
    assert result.comprehensive_analysis is True


def test_agent_analysis_state():
    """Test AgentAnalysisState model"""
    state = AgentAnalysisState(
        document_content="Test patent content",
        document_id=1,
        version_number=2
    )
    
    assert state.document_content == "Test patent content"
    assert state.document_id == 1
    assert state.version_number == 2
    assert state.previous_analyses == {}


def test_agent_analysis_state_minimal():
    """Test AgentAnalysisState with only required field"""
    state = AgentAnalysisState(document_content="Minimal content")
    
    assert state.document_content == "Minimal content"
    assert state.document_id is None
    assert state.version_number is None


def test_model_to_dict():
    """Test that models can be converted to dict"""
    issue = StructuralIssue(
        type="format_error",
        severity="low",
        description="Minor formatting issue",
        suggestion="Fix formatting"
    )
    
    issue_dict = issue.model_dump()
    assert isinstance(issue_dict, dict)
    assert issue_dict["type"] == "format_error"
    assert issue_dict["severity"] == "low"


def test_model_from_dict():
    """Test that models can be created from dict"""
    data = {
        "type": "claim_issue",
        "severity": "high",
        "description": "Claim dependency issue",
        "suggestion": "Fix dependencies"
    }
    
    issue = StructuralIssue(**data)
    assert issue.type == "claim_issue"
    assert issue.severity == "high"
