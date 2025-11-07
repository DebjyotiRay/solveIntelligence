"""
Indian Law PDF Ingestion Script - LOCAL EMBEDDINGS

Extracts text from official Indian law PDFs and creates embeddings using LOCAL models.
Processes:
- Indian Patent Act, 1970
- Indian Penal Code (IPC), 1860
- Indian Evidence Act, 1872
- Constitution of India

Uses:
- sentence-transformers for FREE local embeddings
- ChromaDB for vector storage
- PyMuPDF for PDF extraction

NO OpenAI API calls = $0 cost!
"""

import os
import sys
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import logging
import uuid

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
        pdf_dir: str = "data/indian_laws",
        db_path: str = "db",
        model_name: str = "BAAI/bge-large-en-v1.5"
    ):
        self.pdf_dir = Path(pdf_dir)
        self.db_path = db_path

        # Load local embedding model (FREE!)
        logger.info(f"Loading embedding model: {model_name}")
        logger.info("(First run downloads ~1.3GB, then cached locally)")

        try:
            self.embedding_model = SentenceTransformer(model_name)
            embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"✓ Model loaded (dimensions: {embedding_dim})")
        except Exception as e:
            logger.warning(f"Failed to load {model_name}, using fallback: {e}")
            self.embedding_model = SentenceTransformer("all-mpnet-base-v2")
            logger.info("✓ Fallback model loaded (dimensions: 768)")

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Create/get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="indian_legal_knowledge_local",
            metadata={"description": "Indian law with local embeddings"}
        )
        logger.info("✓ ChromaDB collection ready")

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

    async def process_and_ingest(self):
        """Main processing pipeline"""
        print("\n" + "="*80)
        print("INDIAN LAW PDF PROCESSING AND INGESTION")
        print("="*80)

        stats = {
            "total_processed": 0,
            "total_ingested": 0,
            "total_failed": 0
        }

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
            pdf_path = self.pdf_dir / config["filename"]

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

            # Ingest with LOCAL embeddings (batch processing for speed)
            print("💾 Ingesting with local embeddings (FREE!)...")
            ingested = 0
            failed = 0

            # Process in batches for efficiency
            batch_size = 50
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]

                try:
                    # Prepare batch data
                    ids = []
                    texts = []
                    embeddings = []
                    metadatas = []

                    for chunk in batch:
                        # Create full text
                        section = chunk.get("section", "")
                        title = chunk.get("title", "")
                        content = chunk.get("content", "")
                        full_text = f"Section {section}: {title}\n\n{content}"

                        # Generate embedding locally (FREE!)
                        embedding = self.embedding_model.encode(
                            full_text,
                            convert_to_tensor=False,
                            show_progress_bar=False
                        ).tolist()

                        # Prepare data
                        doc_id = f"legal_{uuid.uuid4().hex[:12]}"
                        metadata = {k: v for k, v in chunk.items() if k != "content"}

                        ids.append(doc_id)
                        texts.append(full_text)
                        embeddings.append(embedding)
                        metadatas.append(metadata)

                    # Batch insert into ChromaDB
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas
                    )

                    ingested += len(batch)
                    print(f"  ✓ Batch {i//batch_size + 1}: {len(batch)} sections ingested")

                except Exception as e:
                    print(f"  ✗ Failed batch {i//batch_size + 1}: {e}")
                    failed += len(batch)

            print(f"\n✅ {config['name']}: {ingested} ingested, {failed} failed")
            stats["total_ingested"] += ingested
            stats["total_failed"] += failed

        # Final summary
        print(f"\n{'='*80}")
        print("INGESTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total chunks processed: {stats['total_processed']}")
        print(f"✓ Successfully ingested: {stats['total_ingested']}")
        print(f"✗ Failed: {stats['total_failed']}")
        print(f"💰 Total cost: $0.00 (local embeddings!)")

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

            # Search ChromaDB
            results = self.collection.query(
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
        print("✅ INGESTION COMPLETE!")
        print(f"{'='*80}")
        print(f"\n🎉 Successfully ingested {stats['total_ingested']} legal document sections!")
        print(f"💾 Stored in: {self.db_path}/chroma.sqlite3")
        print(f"💰 Total cost: $0.00 (100% local)")
        print(f"⚡ Model: {self.embedding_model}")
        print("\nYour unified legal memory now contains:")
        print("  • Indian Patent Act sections")
        print("  • Indian Penal Code sections")
        print("  • Indian Evidence Act sections")
        print("  • Constitution of India articles")
        print("\nReady for:")
        print("  ✓ AI agent legal analysis")
        print("  ✓ Real-time inline suggestions")
        print("  ✓ Semantic search across Indian law")


async def main():
    """Run the ingestion pipeline with local embeddings"""

    print("\n" + "="*80)
    print("INDIAN LAW INGESTION - LOCAL EMBEDDINGS")
    print("="*80)
    print("Using: sentence-transformers + ChromaDB")
    print("Model: BAAI/bge-large-en-v1.5 (best for legal documents)")
    print("Cost: $0.00 (no API calls)")
    print("="*80)

    # Initialize processor
    processor = IndianLawPDFProcessor(
        pdf_dir="data/indian_laws",
        db_path="db",
        model_name="BAAI/bge-large-en-v1.5"
    )

    # Run ingestion
    await processor.process_and_ingest()


if __name__ == "__main__":
    asyncio.run(main())
