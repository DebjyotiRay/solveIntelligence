"""
3-Tier Knowledge Ingestion Script - LOCAL EMBEDDINGS

Level 1: Legal Knowledge (Global)
- data/indian_laws/ → ChromaDB "indian_legal_knowledge_local"
- Indian Patent Act, IPC, Constitution, etc.

Level 2: Firm Knowledge (Firm-wide)
- data/firm_knowledge/ → ChromaDB "firm_knowledge_local"
- Firm's successful patents, templates, style guides

Level 3: Case Knowledge (Project-specific)
- Uploaded via API → Mem0 "episodic_client_memory"
- Invention disclosures, prior art, specs

Uses:
- sentence-transformers for FREE local embeddings
- ChromaDB for vector storage
- PyMuPDF for PDF extraction

"""

import os
import sys
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

# PDF processing
import fitz  # PyMuPDF

# Local embeddings
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class IndianLawPDFProcessor:
    """Process Indian law PDFs and extract structured sections with local embeddings"""

    def __init__(
        self,
        legal_pdf_dir: str = "data/indian_laws",
        firm_pdf_dir: str = "data/firm_knowledge",
        db_path: str = "db"
    ):
        self.legal_pdf_dir = Path(legal_pdf_dir)
        self.firm_pdf_dir = Path(firm_pdf_dir)
        self.db_path = db_path

        # Load local embedding model (all-mpnet-base-v2)
        logger.info("Loading all-mpnet-base-v2 (768 dimensions, optimized for semantic similarity)")
        self.embedding_model = SentenceTransformer("all-mpnet-base-v2")
        logger.info("✓ Embedding model loaded")

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Create/get Level 1 collection (Legal Knowledge)
        self.legal_collection = self.chroma_client.get_or_create_collection(
            name="indian_legal_knowledge_local",
            metadata={"description": "Indian law with local embeddings", "level": "1_legal"}
        )
        logger.info("✓ Legal knowledge collection ready")

        # Create/get Level 2 collection (Firm Knowledge)
        self.firm_collection = self.chroma_client.get_or_create_collection(
            name="firm_knowledge_local",
            metadata={"description": "Firm knowledge with local embeddings", "level": "2_firm"}
        )
        logger.info("✓ Firm knowledge collection ready")

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract all text from a PDF file"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return ""

    def chunk_patent_act(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk Indian Patent Act into sections.
        Pattern: Section numbers like "3.", "10.", "25(1)", "Section 3(k)", etc.
        """
        chunks = []

        # Try to split by section patterns
        # Pattern 1: "Section XX" or "XX."
        section_pattern = r'(?:Section\s+)?(\d+[A-Za-z]?(?:\([a-z0-9]+\))?)\s*[:\.]?\s*([^\n]+)?'

        # Split into rough sections
        sections = re.split(r'\n(?=Section\s+\d+|^\d+\.)', text, flags=re.MULTILINE)

        for section_text in sections:
            section_text = section_text.strip()
            if len(section_text) < 50:  # Skip very short fragments
                continue

            # Try to extract section number and title
            match = re.match(section_pattern, section_text, re.IGNORECASE)

            if match:
                section_num = match.group(1)
                title = match.group(2) if match.group(2) else "Untitled"

                # Clean up title
                title = title.strip().strip('.:-')

                # Limit chunk size (take first 2000 chars to avoid huge chunks)
                content = section_text[:3000]

                chunks.append({
                    "section": section_num,
                    "title": title,
                    "content": content,
                    "source": "Indian Patent Act, 1970",
                    "document_type": "statute",
                    "category": "patent_law",
                    "topic": f"section_{section_num}"
                })

        return chunks

    def chunk_ipc(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk Indian Penal Code into sections.
        Pattern: Section numbers like "120A", "302", "420", etc.
        """
        chunks = []

        # IPC sections are numbered differently
        sections = re.split(r'\n(?=\d+[A-Z]?\.?\s+[A-Z])', text, flags=re.MULTILINE)

        for section_text in sections:
            section_text = section_text.strip()
            if len(section_text) < 50:
                continue

            # Extract section number (e.g., "120A", "302", "420")
            match = re.match(r'(\d+[A-Z]?)\s*\.?\s*([^\n\.]+)?', section_text)

            if match:
                section_num = match.group(1)
                title = match.group(2) if match.group(2) else "Untitled"
                title = title.strip().strip('.:-')

                content = section_text[:3000]

                # Categorize by section number ranges
                category = "general"
                if section_num.startswith("1"):
                    category = "general_explanations"
                elif 120 <= int(re.sub(r'\D', '', section_num)) <= 130:
                    category = "offences_general"
                elif 300 <= int(re.sub(r'\D', '', section_num)) <= 377:
                    category = "offences_against_body"
                elif 378 <= int(re.sub(r'\D', '', section_num)) <= 462:
                    category = "offences_property"
                elif 463 <= int(re.sub(r'\D', '', section_num)) <= 489:
                    category = "offences_documents"

                chunks.append({
                    "section": section_num,
                    "title": title,
                    "content": content,
                    "source": "Indian Penal Code, 1860",
                    "document_type": "criminal_law",
                    "category": category,
                    "topic": f"ipc_{section_num}"
                })

        return chunks

    def chunk_evidence_act(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk Indian Evidence Act into sections.
        """
        chunks = []

        sections = re.split(r'\n(?=\d+\.?\s+[A-Z])', text, flags=re.MULTILINE)

        for section_text in sections:
            section_text = section_text.strip()
            if len(section_text) < 50:
                continue

            match = re.match(r'(\d+)\s*\.?\s*([^\n\.]+)?', section_text)

            if match:
                section_num = match.group(1)
                title = match.group(2) if match.group(2) else "Untitled"
                title = title.strip().strip('.:-')

                content = section_text[:3000]

                chunks.append({
                    "section": section_num,
                    "title": title,
                    "content": content,
                    "source": "Indian Evidence Act, 1872",
                    "document_type": "evidence_law",
                    "category": "evidence",
                    "topic": f"evidence_{section_num}"
                })

        return chunks

    def chunk_constitution(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk Constitution of India into articles.
        Pattern: Article numbers like "Article 14", "Article 19", etc.
        """
        chunks = []

        # Look for "Article XX" pattern
        sections = re.split(r'\n(?=Article\s+\d+)', text, flags=re.IGNORECASE | re.MULTILINE)

        for section_text in sections:
            section_text = section_text.strip()
            if len(section_text) < 50:
                continue

            match = re.match(r'Article\s+(\d+[A-Z]?)\s*\.?\s*([^\n\.]+)?', section_text, re.IGNORECASE)

            if match:
                article_num = match.group(1)
                title = match.group(2) if match.group(2) else "Untitled"
                title = title.strip().strip('.:-')

                content = section_text[:3000]

                # Categorize articles
                category = "general"
                article_int = int(re.sub(r'\D', '', article_num))
                if 12 <= article_int <= 35:
                    category = "fundamental_rights"
                elif 36 <= article_int <= 51:
                    category = "directive_principles"
                elif 52 <= article_int <= 151:
                    category = "union_government"

                chunks.append({
                    "section": f"Article {article_num}",
                    "title": title,
                    "content": content,
                    "source": "Constitution of India",
                    "document_type": "constitutional_law",
                    "category": category,
                    "topic": f"article_{article_num}"
                })

        return chunks

    def chunk_firm_document(self, text: str, filename: str, firm_id: str = "default_firm") -> List[Dict[str, Any]]:
        """
        Chunk firm documents (patents, templates) into manageable pieces.

        Uses simple paragraph-based chunking since firm docs don't have
        structured sections like legal statutes.
        """
        chunks = []

        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk = ""
        chunk_num = 0

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 50:
                continue

            # If adding this para would exceed chunk size, save current chunk
            if len(current_chunk) + len(para) > 2000 and current_chunk:
                chunk_num += 1
                chunks.append({
                    "section": f"chunk_{chunk_num}",
                    "title": f"{filename} - Part {chunk_num}",
                    "content": current_chunk,
                    "source": filename,
                    "document_type": "firm_document",
                    "firm_id": firm_id,
                    "category": "firm_knowledge"
                })
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add final chunk
        if current_chunk:
            chunk_num += 1
            chunks.append({
                "section": f"chunk_{chunk_num}",
                "title": f"{filename} - Part {chunk_num}",
                "content": current_chunk,
                "source": filename,
                "document_type": "firm_document",
                "firm_id": firm_id,
                "category": "firm_knowledge"
            })

        return chunks

    async def process_and_ingest_firm_knowledge(self):
        """Ingest firm knowledge from data/firm_knowledge/ directory"""
        print("\n" + "="*80)
        print("FIRM KNOWLEDGE INGESTION (Level 2)")
        print("="*80)

        if not self.firm_pdf_dir.exists():
            print(f"⚠️  Directory {self.firm_pdf_dir} not found. Creating it...")
            self.firm_pdf_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created {self.firm_pdf_dir}")
            print("   Place firm PDFs (successful patents, templates) here and run again.")
            return {"status": "directory_created", "files_processed": 0}

        # Get all PDFs in firm_knowledge directory
        pdf_files = list(self.firm_pdf_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"ℹ️  No PDF files found in {self.firm_pdf_dir}")
            print("   This is optional - firm knowledge can be empty.")
            return {"status": "empty", "files_processed": 0}

        print(f"Found {len(pdf_files)} firm documents to process")

        total_ingested = 0
        total_failed = 0

        for pdf_path in pdf_files:
            print(f"\n{'='*80}")
            print(f"Processing: {pdf_path.name}")
            print(f"{'='*80}")

            # Extract text
            print("📄 Extracting text...")
            text = self.extract_text_from_pdf(pdf_path)
            print(f"✓ Extracted {len(text)} characters")

            if len(text) < 100:
                print(f"⚠️  Insufficient content, skipping")
                total_failed += 1
                continue

            # Chunk the document
            print("✂️  Chunking document...")
            chunks = self.chunk_firm_document(text, pdf_path.name)
            print(f"✓ Created {len(chunks)} chunks")

            # Ingest to firm_knowledge_local collection
            print("💾 Ingesting to firm knowledge collection...")
            ingested = 0

            try:
                # Prepare batch
                ids = []
                texts = []
                metadatas = []

                for chunk in chunks:
                    full_text = f"{chunk['title']}\n\n{chunk['content']}"
                    doc_id = f"firm_{uuid.uuid4().hex[:12]}"
                    metadata = {k: v for k, v in chunk.items() if k != "content"}

                    ids.append(doc_id)
                    texts.append(full_text)
                    metadatas.append(metadata)

                # Generate embeddings in batch
                embeddings = self.embedding_model.encode(
                    texts,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    batch_size=32
                )
                embeddings = [emb.tolist() for emb in embeddings]

                # Insert into firm collection
                self.firm_collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )

                ingested = len(chunks)
                total_ingested += ingested
                print(f"✅ {pdf_path.name}: {ingested} chunks ingested")

            except Exception as e:
                print(f"❌ Failed to ingest {pdf_path.name}: {e}")
                total_failed += 1

        print(f"\n{'='*80}")
        print("FIRM KNOWLEDGE INGESTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total chunks ingested: {total_ingested}")
        print(f"Failed files: {total_failed}")
        print(f"💰 Total cost: $0.00 (local embeddings)")

        return {
            "status": "complete",
            "files_processed": len(pdf_files) - total_failed,
            "total_chunks": total_ingested
        }

    async def process_and_ingest(self):
        """Main processing pipeline - Ingests both legal and firm knowledge"""
        print("\n" + "="*80)
        print("3-TIER KNOWLEDGE INGESTION PIPELINE")
        print("="*80)
        print("Level 1: Legal Knowledge (data/indian_laws/)")
        print("Level 2: Firm Knowledge (data/firm_knowledge/)")
        print("="*80)

        stats = {
            "total_processed": 0,
            "total_ingested": 0,
            "total_failed": 0
        }

        # ========== LEVEL 1: LEGAL KNOWLEDGE ==========
        print("\n" + "="*80)
        print("LEVEL 1: LEGAL KNOWLEDGE INGESTION")
        print("="*80)

        # Process each PDF
        pdf_configs = [
            {
                "filename": "indian_patent_act_1970.pdf",
                "name": "Indian Patent Act, 1970",
                "chunker": self.chunk_patent_act
            },
            {
                "filename": "indian_penal_code_1860.pdf",
                "name": "Indian Penal Code, 1860",
                "chunker": self.chunk_ipc
            },
            {
                "filename": "indian_evidence_act_1872.pdf",
                "name": "Indian Evidence Act, 1872",
                "chunker": self.chunk_evidence_act
            },
            {
                "filename": "constitution_of_india.pdf",
                "name": "Constitution of India",
                "chunker": self.chunk_constitution
            }
        ]

        for config in pdf_configs:
            pdf_path = self.legal_pdf_dir / config["filename"]

            print(f"\n{'='*80}")
            print(f"Processing: {config['name']}")
            print(f"File: {pdf_path}")
            print(f"{'='*80}")

            if not pdf_path.exists():
                print(f"❌ PDF not found: {pdf_path}")
                continue

            # Extract text
            print("📄 Extracting text from PDF...")
            text = self.extract_text_from_pdf(pdf_path)
            print(f"✓ Extracted {len(text)} characters")

            # Chunk into sections
            print("✂️  Chunking into sections...")
            chunks = config["chunker"](text)
            print(f"✓ Created {len(chunks)} chunks")

            stats["total_processed"] += len(chunks)

            # Ingest with LOCAL embeddings (PARALLEL processing for speed on MPS!)
            print("💾 Ingesting with parallel local embeddings (FREE!)...")
            ingested = 0
            failed = 0

            # Process in batches for efficiency
            batch_size = 100  # Increased batch size for parallel processing
            num_workers = 4    # Parallel workers for MPS
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]

                try:
                    # Prepare batch data
                    ids = []
                    texts = []
                    metadatas = []

                    # Prepare full texts
                    for chunk in batch:
                        section = chunk.get("section", "")
                        title = chunk.get("title", "")
                        content = chunk.get("content", "")
                        full_text = f"Section {section}: {title}\n\n{content}"
                        
                        doc_id = f"legal_{uuid.uuid4().hex[:12]}"
                        metadata = {k: v for k, v in chunk.items() if k != "content"}

                        ids.append(doc_id)
                        texts.append(full_text)
                        metadatas.append(metadata)

                    # PARALLEL EMBEDDING GENERATION for MPS acceleration
                    # Encode all texts in batch (much faster than one-by-one)
                    embeddings = self.embedding_model.encode(
                        texts,
                        convert_to_tensor=False,
                        show_progress_bar=False,
                        batch_size=32  # Sub-batch size for model
                    )
                    
                    # Convert to list format
                    embeddings = [emb.tolist() for emb in embeddings]

                    # Batch insert into ChromaDB legal collection
                    self.legal_collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas
                    )

                    ingested += len(batch)
                    print(f"  ✓ Batch {i//batch_size + 1}: {len(batch)} sections ingested (parallel)")

                except Exception as e:
                    print(f"  ✗ Failed batch {i//batch_size + 1}: {e}")
                    failed += len(batch)

            print(f"\n✅ {config['name']}: {ingested} ingested, {failed} failed")
            stats["total_ingested"] += ingested
            stats["total_failed"] += failed

        # Legal knowledge summary
        print(f"\n{'='*80}")
        print("LEVEL 1 INGESTION SUMMARY (Legal Knowledge)")
        print(f"{'='*80}")
        print(f"Total chunks processed: {stats['total_processed']}")
        print(f"✓ Successfully ingested: {stats['total_ingested']}")
        print(f"✗ Failed: {stats['total_failed']}")
        print(f"💰 Total cost: $0.00 (local embeddings!)")

        # ========== LEVEL 2: FIRM KNOWLEDGE ==========
        firm_result = await self.process_and_ingest_firm_knowledge()

        # Combined summary
        print(f"\n{'='*80}")
        print("COMPLETE INGESTION SUMMARY")
        print(f"{'='*80}")
        print(f"Level 1 (Legal): {stats['total_ingested']} chunks")
        print(f"Level 2 (Firm): {firm_result.get('total_chunks', 0)} chunks")
        print(f"💰 Total cost: $0.00 (100% local embeddings!)")

        # Verify with test queries
        print(f"\n{'='*80}")
        print("VERIFICATION - Testing Semantic Search with Local Embeddings")
        print(f"{'='*80}")

        test_queries = [
            "Section 3(k) computer programs software patentability",
            "IPC Section 420 fraud cheating",
            "Section 65B electronic evidence digital records",
            "Article 21 life and personal liberty fundamental rights"
        ]

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")

            # Generate query embedding locally
            query_embedding = self.embedding_model.encode(
                query,
                convert_to_tensor=False,
                show_progress_bar=False
            ).tolist()

            # Search ChromaDB legal collection
            results = self.legal_collection.query(
                query_embeddings=[query_embedding],
                n_results=2
            )

            if results['ids'] and len(results['ids'][0]) > 0:
                print(f"   Found {len(results['ids'][0])} results:")
                for i in range(len(results['ids'][0])):
                    doc = results['documents'][0][i][:120]
                    meta = results['metadatas'][0][i]
                    print(f"   {i+1}. {meta.get('source', 'Unknown')}, {meta.get('section', '')}")
                    print(f"      {doc}...")
            else:
                print("   No results found")

        print(f"\n{'='*80}")
        print("✅ 3-TIER INGESTION COMPLETE!")
        print(f"{'='*80}")
        print(f"\n🎉 Successfully ingested knowledge into 3-tier hierarchy!")
        print(f"💾 Stored in: {self.db_path}/chroma.sqlite3")
        print(f"💰 Total cost: $0.00 (100% local)")
        print(f"⚡ Model: {self.embedding_model}")
        print("\n📚 3-TIER KNOWLEDGE HIERARCHY:")
        print("  Level 1 (Legal - Global):")
        print("    • Indian Patent Act sections")
        print("    • Indian Penal Code sections")
        print("    • Indian Evidence Act sections")
        print("    • Constitution of India articles")
        print(f"    → {stats['total_ingested']} chunks in 'indian_legal_knowledge_local'")
        print("\n  Level 2 (Firm - Firm-wide):")
        print(f"    • Firm's successful patents & templates")
        print(f"    → {firm_result.get('total_chunks', 0)} chunks in 'firm_knowledge_local'")
        print("\n  Level 3 (Case - Project-specific):")
        print("    • Case documents uploaded via API")
        print("    → Stored in 'episodic_client_memory' (Mem0)")
        print("\n✅ Ready for:")
        print("  ✓ AI agent legal analysis with firm context")
        print("  ✓ Real-time inline suggestions")
        print("  ✓ Semantic search across all knowledge levels")


async def main():
    """Run the ingestion pipeline with local embeddings"""

    print("\n" + "="*80)
    print("INDIAN LAW INGESTION - LOCAL EMBEDDINGS")
    print("="*80)
    print("Using: all-mpnet-base-v2 (sentence-transformers) + ChromaDB")
    print("Model: Optimized for semantic similarity (768 dimensions)")
    print("Cost: $0.00 (100% local, no API calls)")
    print("="*80)

    # Initialize processor
    processor = IndianLawPDFProcessor(
        legal_pdf_dir="data/indian_laws",
        firm_pdf_dir="data/firm_knowledge",
        db_path="db"
    )

    # Run ingestion
    await processor.process_and_ingest()


if __name__ == "__main__":
    asyncio.run(main())
