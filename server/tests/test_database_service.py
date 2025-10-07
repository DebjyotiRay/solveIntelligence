"""
Tests for DatabaseService
"""
from app.services.database_service import DatabaseService
from app.models import Document, DocumentVersion


def test_get_document(test_db):
    """Test getting a document"""
    # Create test document
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    doc_id = doc.id
    
    # Test retrieval
    result = DatabaseService.get_document(test_db, doc_id)
    assert result is not None
    assert result.id == doc_id
    assert result.title == "Test Patent"


def test_get_document_not_found(test_db):
    """Test getting non-existent document"""
    result = DatabaseService.get_document(test_db, 9999)
    assert result is None


def test_create_document_version(test_db):
    """Test creating a new version"""
    # Create document
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    # Create version
    version = DatabaseService.create_document_version(
        test_db, doc.id, "Version 1 content", "Version 1"
    )
    
    assert version is not None
    assert version.document_id == doc.id
    assert version.version_number == 1
    assert version.content == "Version 1 content"
    assert version.name == "Version 1"


def test_create_multiple_versions(test_db):
    """Test creating multiple versions with auto-increment"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    # Create 3 versions
    v1 = DatabaseService.create_document_version(test_db, doc.id, "Content 1")
    v2 = DatabaseService.create_document_version(test_db, doc.id, "Content 2")
    v3 = DatabaseService.create_document_version(test_db, doc.id, "Content 3")
    
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v3.version_number == 3


def test_get_latest_version(test_db):
    """Test getting latest version"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    # Create versions
    DatabaseService.create_document_version(test_db, doc.id, "Old content")
    latest = DatabaseService.create_document_version(test_db, doc.id, "Latest content")
    
    # Get latest
    result = DatabaseService.get_latest_version(test_db, doc.id)
    assert result is not None
    assert result.version_number == latest.version_number
    assert result.content == "Latest content"


def test_get_document_versions(test_db):
    """Test getting all versions for a document"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    # Create 3 versions
    for i in range(1, 4):
        DatabaseService.create_document_version(test_db, doc.id, f"Content {i}")
    
    versions = DatabaseService.get_document_versions(test_db, doc.id)
    assert len(versions) == 3
    assert all(v.document_id == doc.id for v in versions)


def test_get_document_version_specific(test_db):
    """Test getting a specific version"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    DatabaseService.create_document_version(test_db, doc.id, "V1")
    DatabaseService.create_document_version(test_db, doc.id, "V2")
    
    # Get version 1
    version = DatabaseService.get_document_version(test_db, doc.id, 1)
    assert version is not None
    assert version.version_number == 1
    assert version.content == "V1"


def test_update_document_version(test_db):
    """Test updating a version"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    v1 = DatabaseService.create_document_version(test_db, doc.id, "Original")
    
    # Update it
    updated = DatabaseService.update_document_version(
        test_db, doc.id, 1, "Updated content", "Updated name"
    )
    
    assert updated.content == "Updated content"
    assert updated.name == "Updated name"


def test_delete_document_version(test_db):
    """Test deleting a version"""
    doc = Document(title="Test Patent", current_version=1)
    test_db.add(doc)
    test_db.commit()
    
    v1 = DatabaseService.create_document_version(test_db, doc.id, "V1")
    v2 = DatabaseService.create_document_version(test_db, doc.id, "V2")
    
    # Delete v1
    DatabaseService.delete_document_version(test_db, doc.id, 1)
    
    # Verify deleted
    result = DatabaseService.get_document_version(test_db, doc.id, 1)
    assert result is None
    
    # V2 should still exist
    result = DatabaseService.get_document_version(test_db, doc.id, 2)
    assert result is not None


def test_seed_initial_data(test_db):
    """Test seeding initial data"""
    seed_data = [
        {"id": 1, "title": "Patent 1", "content": "Content 1"},
        {"id": 2, "title": "Patent 2", "content": "Content 2"}
    ]
    
    DatabaseService.seed_initial_data(test_db, seed_data)
    
    # Verify documents created
    doc1 = DatabaseService.get_document(test_db, 1)
    doc2 = DatabaseService.get_document(test_db, 2)
    
    assert doc1 is not None
    assert doc2 is not None
    assert doc1.title == "Patent 1"
    assert doc2.title == "Patent 2"
    
    # Verify versions created
    v1 = DatabaseService.get_latest_version(test_db, 1)
    v2 = DatabaseService.get_latest_version(test_db, 2)
    
    assert v1 is not None
    assert v2 is not None
    assert v1.content == "Content 1"
    assert v2.content == "Content 2"
