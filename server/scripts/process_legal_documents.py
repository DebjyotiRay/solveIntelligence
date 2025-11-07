"""
Legal Document Processor
Extracts text from PDFs and processes them into mem0 memory chunks
"""

import PyPDF2
import re
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LegalDocumentProcessor:
    """Process legal PDFs into memory-ready chunks"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize processor
        
        Args:
            chunk_size: Target size of each text chunk (characters)
            overlap: Overlap between chunks for context preservation
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text as string
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                logger.info(f"Extracted {len(text)} characters from {pdf_path}")
                return text
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove page markers but keep content
        text = re.sub(r'--- Page \d+ ---', '', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        text_length = len(text)
        start = 0
        chunk_index = 0
        
        while start < text_length:
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence end markers
                last_period = max(
                    chunk_text.rfind('. '),
                    chunk_text.rfind('.\n'),
                    chunk_text.rfind('? '),
                    chunk_text.rfind('! ')
                )
                
                # Use sentence boundary if found in last 30% of chunk
                if last_period > self.chunk_size * 0.7:
                    end = start + last_period + 1
                    chunk_text = text[start:end]
            
            chunks.append({
                'text': chunk_text.strip(),
                'chunk_index': chunk_index,
                'start_char': start,
                'end_char': end,
                'length': len(chunk_text)
            })
            
            chunk_index += 1
            start = end - self.overlap
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect section numbers in legal text
        
        Args:
            text: Legal document text
            
        Returns:
            List of detected sections with positions
        """
        sections = []
        
        # Pattern for "Section X" or "Section X(y)"
        pattern = r'Section\s+(\d+[A-Z]?(?:\([a-z0-9]+\))?)'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            sections.append({
                'section': match.group(1),
                'position': match.start(),
                'full_text': match.group(0)
            })
        
        logger.info(f"Detected {len(sections)} section references")
        return sections
    
    def process_patent_act(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process Indian Patent Act PDF
        
        Args:
            pdf_path: Path to Patent Act PDF
            
        Returns:
            List of processed chunks with metadata
        """
        logger.info(f"Processing Patent Act from {pdf_path}")
        
        # Extract and clean text
        raw_text = self.extract_pdf_text(pdf_path)
        clean_text = self.clean_text(raw_text)
        
        # Detect sections
        sections = self.detect_sections(clean_text)
        
        # Create chunks
        chunks = self.chunk_text(clean_text)
        
        # Add metadata to chunks
        for chunk in chunks:
            chunk['source'] = 'Indian Patent Act 1970'
            chunk['document_type'] = 'statute'
            chunk['category'] = 'patent_law'
            
            # Find which section this chunk might belong to
            chunk_start = chunk['start_char']
            relevant_section = None
            for section in sections:
                if section['position'] <= chunk_start:
                    relevant_section = section['section']
                else:
                    break
            
            if relevant_section:
                chunk['section'] = relevant_section
        
        logger.info(f"Processed Patent Act into {len(chunks)} chunks")
        return chunks
    
    def process_ipc(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process Indian Penal Code PDF
        
        Args:
            pdf_path: Path to IPC PDF
            
        Returns:
            List of processed chunks with metadata
        """
        logger.info(f"Processing IPC from {pdf_path}")
        
        # Extract and clean text
        raw_text = self.extract_pdf_text(pdf_path)
        clean_text = self.clean_text(raw_text)
        
        # Detect sections
        sections = self.detect_sections(clean_text)
        
        # Create chunks
        chunks = self.chunk_text(clean_text)
        
        # Add metadata to chunks
        for chunk in chunks:
            chunk['source'] = 'Indian Penal Code 1860'
            chunk['document_type'] = 'criminal_law'
            chunk['category'] = 'penal_code'
            
            # Find which section this chunk might belong to
            chunk_start = chunk['start_char']
            relevant_section = None
            for section in sections:
                if section['position'] <= chunk_start:
                    relevant_section = section['section']
                else:
                    break
            
            if relevant_section:
                chunk['section'] = relevant_section
        
        logger.info(f"Processed IPC into {len(chunks)} chunks")
        return chunks
    
    def process_generic_legal_doc(
        self, 
        pdf_path: str,
        source_name: str,
        doc_type: str,
        category: str
    ) -> List[Dict[str, Any]]:
        """
        Process any legal PDF document
        
        Args:
            pdf_path: Path to PDF
            source_name: Name of the legal source
            doc_type: Type of document
            category: Category classification
            
        Returns:
            List of processed chunks with metadata
        """
        logger.info(f"Processing {source_name} from {pdf_path}")
        
        # Extract and clean text
        raw_text = self.extract_pdf_text(pdf_path)
        clean_text = self.clean_text(raw_text)
        
        # Create chunks
        chunks = self.chunk_text(clean_text)
        
        # Add metadata to chunks
        for chunk in chunks:
            chunk['source'] = source_name
            chunk['document_type'] = doc_type
            chunk['category'] = category
        
        logger.info(f"Processed {source_name} into {len(chunks)} chunks")
        return chunks
