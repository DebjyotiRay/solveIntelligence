# Task 1: Document Versioning - Technical Documentation

## 🎯 What We Built
A stateless document versioning system with Google Docs-style UX:
1. Create new versions of patent documents
2. Switch between existing versions 
3. Edit and save changes to any version

## 🏗️ Low Level Design (LLD)

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Client  │    │  FastAPI Server │    │   PostgreSQL    │
│                 │    │                 │    │                 │
│ - Version State │◄──►│ - Version APIs  │◄──►│ - Document      │
│ - Content Edit  │    │ - Race Condition│    │ - DocumentVer   │
│ - UX Logic      │    │   Prevention    │    │ - Constraints   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Database Schema
```sql
Document: 
  id (PK), title

DocumentVersion:
  id (PK), document_id (FK), version_number, content, created_at, name
  UNIQUE(document_id, version_number)  -- Prevents race conditions
```

### API Layer
```python
# Core endpoints with atomic operations
POST   /document/{id}/versions     # Create with SELECT FOR UPDATE lock
PUT    /document/{id}/versions/{v} # Update specific version
GET    /document/{id}/versions     # List all versions
```

## 🔄 Sequence Flow Diagrams

### 1. Create New Version Flow
```
Frontend          Backend                Database
   │                 │                     │
   │─── POST /versions ──►                 │
   │    {content, name}   │                │
    │                     │                 │
    │                     │─── BEGIN ──────►│
    │                     │                 │
    │                     │─ SELECT max(ver)│
    │                     │   FOR UPDATE ──►│
    │                     │                 │
    │                     │◄── max_ver ─────│
    │                     │                 │
    │                     │─── INSERT ─────►│
    │                     │   new_version   │
    │                     │                 │
    │                     │─── COMMIT ─────►│
    │                     │                 │
    │◄─── 201 new_version ─│                │
   │                     │                 │
   │ Update UI State     │                 │
   │ - Add to versions[] │                 │
   │ - Switch to new ver │                 │
```

### 2. Version Switch Flow
```
Frontend          (Local State Only)
   │
   │ User selects different version
   │
   │ IF isDirty?
   ├──► Show Warning Dialog
   │    "Unsaved changes will be lost"
   │
   │ User confirms?
   ├──► Find version in local state
   │    setCurrentContent(version.content)
   │    setSelectedVersion(version_number)
   │    setIsDirty(false)
   │
   │ No API call needed!
```

### 3. Save to Current Version Flow
```
Frontend          Backend                Database
   │                 │                     │
   │── PUT /versions/2 ──►                 │
   │   {content, name}    │                │
   │                     │                 │
   │                     │── UPDATE ──────►│
   │                     │   SET content   │
   │                     │   WHERE id=2    │
   │                     │                 │
   │◄───── 200 OK ───────│                │
   │                     │                 │
   │ setIsDirty(false)   │                 │
```

### 4. Load Document Flow
```
Frontend          Backend                Database
   │                 │                     │
   │─── GET /document/1 ──►                │
   │                     │── SELECT ─────►│
   │                     │   FROM document │
   │◄─── document_info ──│                │
   │                     │                 │
   │─ GET /doc/1/versions ──►              │
   │                     │── SELECT ─────►│
   │                     │   FROM doc_vers │
   │◄─── versions[] ─────│                │
   │                     │                 │
   │ Set latest version  │                 │
   │ as current content  │                 │
```

## 🔧 Component Interactions

### Frontend State Management
```typescript
// Core state structure
interface AppState {
  selectedVersionNumber: number;    // Which version viewing
  currentDocumentContent: string;   // Working content
  availableVersions: Version[];     // Cached versions
  isDirty: boolean;                // Unsaved changes flag
}

// Key functions
loadPatent() → API calls → Update state
switchVersion() → Local state update only
createVersion() → API call → Update state
saveVersion() → API call → Clear dirty flag
```

### Backend Race Condition Prevention
```python
def create_version(document_id, content):
    with db.begin():  # Transaction start
        # Lock to prevent concurrent version creation
        max_ver = db.scalar(
            select(max(version_number))
            .where(document_id == doc_id)
            .with_for_update()  # 🔒 Critical section
        )
        
        new_version = max_ver + 1
        insert_version(doc_id, new_version, content)
        commit()  # Atomic operation complete
```

## ✅ Architecture Benefits

1. **Stateless Design** - No server-side user session state
2. **Race Condition Safe** - Database-level locking prevents conflicts  
3. **Single Source of Truth** - Only DocumentVersion stores content
4. **Fast Version Switching** - Client-side operation, no API calls
5. **Professional UX** - Dirty state warnings, visual indicators

## 🔗 Integration Points for Next Tasks

**For Task 2 (AI Suggestions):**
- `currentDocumentContent` provides clean text for AI analysis
- `selectedVersionNumber` gives version context
- WebSocket can stream suggestions in real-time

**For Task 3 (Custom AI Features):**
- Versioning supports AI-assisted content modifications
- Professional UI foundation for additional features

---

**Result: Enterprise-grade document versioning with atomic operations, professional UX, and clean integration points for AI features.**
