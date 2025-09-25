from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re


def strip_html(content: str) -> str:
    """
    Strip HTML tags and return clean text for AI processing.
    Preserves structure by replacing common block elements with newlines.
    """
    if not content:
        return ""

    # Parse HTML
    soup = BeautifulSoup(content, 'html.parser')

    # Add newlines before block elements for better structure preservation
    for element in soup.find_all(['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        element.insert_before('\n')

    # Get text and clean up whitespace
    text = soup.get_text()

    # Clean up excessive whitespace while preserving paragraph breaks
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines -> double newline
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs -> single space
    text = text.strip()

    return text


def prepare_content_for_ai(content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Prepare document content for AI analysis.

    Args:
        content: Raw HTML content from the document
        context: Additional context like document_id, version_number, user_id

    Returns:
        Dict containing clean_text and metadata for AI processing
    """
    clean_text = strip_html(content)

    # Word count and basic metrics
    word_count = len(clean_text.split())
    char_count = len(clean_text)

    return {
        "clean_text": clean_text,
        "word_count": word_count,
        "char_count": char_count,
        "has_content": bool(clean_text.strip()),
        "context": context or {}
    }


def chunk_content_for_streaming(content: str, chunk_size: int = 1000) -> List[str]:
    """
    Break content into chunks for progressive AI analysis and streaming.

    Args:
        content: Clean text content
        chunk_size: Maximum characters per chunk

    Returns:
        List of text chunks that can be processed independently
    """
    if not content or len(content) <= chunk_size:
        return [content] if content else []

    chunks = []
    words = content.split()
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1  # +1 for space

        if current_length + word_length > chunk_size and current_chunk:
            # Finish current chunk
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length

    # Add remaining chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks