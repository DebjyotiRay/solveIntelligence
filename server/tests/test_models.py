"""
Tests for database models
"""
from app.models import Document, DocumentVersion


def test_document_creation(test_db):
    """Test creating a document"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    assert doc.id is not None
    assert doc.title == "Test Patent"
    assert doc.current_version == 1


def test_document_version_creation(test_db):
    """Test creating a document version"""
    # Create document first
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    # Create version
    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        content="Test content for patent"
    )
    test_db.add(version)
    test_db.commit()
    
    assert version.id is not None
    assert version.document_id == doc.id
    assert version.version_number == 1
    assert version.content == "Test content for patent"


def test_multiple_versions(test_db):
    """Test creating multiple versions"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    # Create 3 versions
    for i in range(1, 4):
        version = DocumentVersion(
            document_id=doc.id,
            version_number=i,
            content=f"Version {i} content"
        )
        test_db.add(version)
    
    test_db.commit()
    
    # Query all versions
    versions = test_db.query(DocumentVersion).filter_by(document_id=doc.id).all()
    assert len(versions) == 3
    assert versions[0].version_number == 1
    assert versions[2].version_number == 3
