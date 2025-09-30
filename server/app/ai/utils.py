"""
Utility functions for AI processing in the multi-agent system.
"""
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