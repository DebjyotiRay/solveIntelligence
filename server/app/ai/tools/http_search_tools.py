import httpx
import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import hashlib
import time

logger = logging.getLogger(__name__)


class PatentAPIClient:
    """
    Real Patent API integration using SearchAPI.io Google Patents API.
    Provides comprehensive patent data with rich metadata and proper relevance ranking.
    Requires SEARCHAPI_API_KEY environment variable.
    """

    def __init__(self):
        # SearchAPI.io Google Patents API - comprehensive, structured patent data
        self.searchapi_base = "https://www.searchapi.io/api/v1/search"
        self.searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        self.has_searchapi_key = bool(self.searchapi_key)
        
        self.session = None
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Respect rate limits
        
        print(f"🔑 PATENT API: SearchAPI.io key {'configured' if self.has_searchapi_key else 'missing (patent search disabled)'}")

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session with proper headers."""
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "PatentAnalysis-MultiAgent/2.0 (Academic Research Tool)",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
        return self.session

    async def _rate_limit(self):
        """Implement rate limiting to respect API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _get_cache_key(self, query: str, params: dict) -> str:
        """Generate cache key for request."""
        cache_data = f"{query}_{str(sorted(params.items()))}"
        return hashlib.md5(cache_data.encode()).hexdigest()

    async def search_patents(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search for real patents using SearchAPI.io Google Patents API.
        Comprehensive patent search with rich metadata and proper relevance ranking.

        Args:
            query: Search query (title, abstract, keywords, inventor, assignee)
            limit: Maximum results to return

        Returns:
            Real patent search results from Google Patents via SearchAPI.io
        """
        print(f"🌐 SearchAPI.io Google Patents: Starting real patent search for query: '{query}'")
        print(f"🌐 SearchAPI.io Google Patents: Search limit: {limit} results")

        try:
            # Check cache first
            cache_key = self._get_cache_key(query, {"limit": limit})
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                print(f"🌐 SearchAPI.io: Using cached result ({len(cached_result['patents'])} patents)")
                return cached_result

            await self._rate_limit()
            session = await self._get_session()

            if self.has_searchapi_key:
                # Use SearchAPI.io Google Patents API - comprehensive and reliable
                params = {
                    "engine": "google_patents",
                    "q": query,
                    "num": limit,
                    "api_key": self.searchapi_key
                }
                
                print(f"🌐 SearchAPI.io: Making real HTTP request to Google Patents...")
                print(f"🌐 SearchAPI.io: URL: {self.searchapi_base}")
                
                start_time = time.time()
                
                response = await session.get(self.searchapi_base, params=params)
                response_time = int((time.time() - start_time) * 1000)
                
                print(f"🌐 SearchAPI.io: Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    patents = []
                    
                    # Parse SearchAPI.io Google Patents response
                    organic_results = data.get("organic_results", [])
                    
                    print(f"🌐 SearchAPI.io: Found {len(organic_results)} organic results")
                    
                    for result in organic_results[:limit]:
                        patent = {
                            "patent_id": result.get("result_id", result.get("link", "Unknown")),
                            "title": result.get("title", "No title available"),
                            "abstract": result.get("snippet", "No abstract available")[:500],
                            "filing_date": result.get("filing_date", "Unknown"),
                            "inventors": result.get("inventors", []),
                            "assignee": result.get("assignee", "Not specified"),
                            "status": result.get("status", "Unknown"),
                            "relevance_score": result.get("position", len(patents) + 1),
                            "patent_family_id": result.get("family_id", "Unknown"),
                            "technology_center": "Unknown",
                            "country": result.get("country", "Unknown"),
                            "publication_number": result.get("publication_number", "Unknown"),
                            "priority_date": result.get("priority_date", "Unknown"),
                            "publication_date": result.get("publication_date", "Unknown"),
                            "link": result.get("link", "")
                        }
                        patents.append(patent)
                    
                    result_data = {
                        "query": query,
                        "total_results": data.get("search_information", {}).get("total_results", len(patents)),
                        "patents": patents,
                        "search_metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "api_source": "SearchAPI.io Google Patents API",
                            "response_time_ms": response_time,
                            "api_version": "google_patents",
                            "status": "success",
                            "note": "Using real Google Patents data via SearchAPI.io - live internet search"
                        }
                    }
                    
                    # Cache the result
                    self.cache[cache_key] = result_data
                    
                    print(f"🌐 SearchAPI.io: Search completed - found {len(patents)} real patents from internet")
                    return result_data
                
                else:
                    error_msg = f"SearchAPI.io returned status {response.status_code}: {response.text[:200]}"
                    print(f"🌐 SearchAPI.io: {error_msg}")
                    raise Exception(error_msg)
            
            else:
                # No SearchAPI key - patent search unavailable
                print(f"🚨 PATENT SEARCH: SearchAPI.io key required for real patent data")
                return {
                    "query": query,
                    "total_results": 0,
                    "patents": [],
                    "error": "Patent search unavailable - SEARCHAPI_API_KEY required",
                    "search_metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "api_source": "SearchAPI.io Google Patents API",
                        "status": "unavailable",
                        "note": "No API key provided - patent search disabled to prevent fake data"
                    }
                }

        except Exception as e:
            print(f"🌐 SearchAPI.io: Search failed - {str(e)}")
            logger.error(f"SearchAPI.io patent search failed: {e}")
            
            # Return error result (not fake data)
            return {
                "query": query,
                "total_results": 0,
                "patents": [],
                "error": str(e),
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "SearchAPI.io Google Patents API",
                    "status": "error",
                    "note": "Real API call failed - no fake data provided"
                }
            }

    async def close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()
            self.session = None


class LegalAPIClient:
    """
    Real Legal Information Institute (LII) API integration.
    Accesses actual 35 USC and CFR regulations from Cornell Law School.
    """

    def __init__(self):
        self.base_url = "https://www.law.cornell.edu/uscode/text"
        self.cfr_url = "https://www.ecfr.gov/api/versioner/v1/full"
        self.session = None
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 2.0  # More conservative rate limiting for legal APIs

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "PatentAnalysis-Research/2.0 (Academic Legal Research)",
                    "Accept": "application/json, text/html"
                }
            )
        return self.session

    async def _rate_limit(self):
        """Implement rate limiting for legal APIs."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    async def get_usc_section(self, title: str, section: str) -> Dict[str, Any]:
        """
        Get real USC section text from Cornell Law's Legal Information Institute.

        Args:
            title: USC Title (e.g., "35" for patent law)
            section: Section number (e.g., "112")

        Returns:
            Real legal text from official sources
        """
        print(f"⚖️  LII API: Fetching real USC {title} § {section}")

        try:
            cache_key = f"usc_{title}_{section}"
            if cache_key in self.cache:
                print(f"⚖️  LII API: Using cached USC {title} § {section}")
                return self.cache[cache_key]

            await self._rate_limit()
            session = await self._get_session()

            # Real Cornell LII API request
            url = f"{self.base_url}/{title}/{section}"
            print(f"⚖️  LII API: Making real HTTP request to Cornell Law...")

            start_time = time.time()
            response = await session.get(url)
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                # Parse the HTML content to extract legal text
                text_content = self._extract_legal_text(response.text)

                result = {
                    "title": title,
                    "section": section,
                    "full_citation": f"{title} U.S.C. § {section}",
                    "text": text_content,
                    "source": "Cornell Law School Legal Information Institute",
                    "search_metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "api_source": "Cornell LII",
                        "response_time_ms": response_time,
                        "status": "success"
                    }
                }

                # Cache the result
                self.cache[cache_key] = result
                print(f"⚖️  LII API: Successfully retrieved USC {title} § {section}")
                return result

            else:
                error_msg = f"Cornell LII returned status {response.status_code}"
                raise Exception(error_msg)

        except Exception as e:
            print(f"⚖️  LII API: Failed to retrieve USC {title} § {section} - {str(e)}")
            logger.error(f"Legal regulation retrieval failed: {e}")
            return {
                "title": title,
                "section": section,
                "text": "",
                "error": str(e),
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "Cornell LII",
                    "status": "error"
                }
            }

    def _extract_legal_text(self, html_content: str) -> str:
        """Extract legal text from HTML response."""
        # Simple HTML parsing to extract legal text
        # In production, use BeautifulSoup for robust parsing
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find the main legal content
            legal_content = soup.find('div', class_='field-item')
            if legal_content:
                return legal_content.get_text(strip=True)

            # Fallback: look for any substantial text content
            text = soup.get_text()
            # Return first 2000 characters as a reasonable excerpt
            return text[:2000] if text else "Legal text not found"

        except ImportError:
            # Fallback without BeautifulSoup
            # Remove HTML tags and extract text (basic approach)
            import re
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:2000] if text else "Legal text not found"

    async def search_regulations(
        self,
        regulation_type: str = "35USC",
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for real legal regulations.

        Args:
            regulation_type: Type of regulation (35USC, CFR, etc.)
            section: Specific section to retrieve

        Returns:
            Real regulation information from official sources
        """
        print(f"⚖️  LEGAL API: Searching real {regulation_type} regulations")
        if section:
            print(f"⚖️  LEGAL API: Specific section: {section}")

        try:
            regulations = {}

            if regulation_type == "35USC":
                # Get key patent law sections
                key_sections = ["101", "102", "103", "112"] if not section else [section]

                for sec in key_sections:
                    usc_data = await self.get_usc_section("35", sec)
                    if usc_data and "error" not in usc_data:
                        regulations[sec] = usc_data["text"]
                    else:
                        # ⚠️  NO FAKE DATA: When real Cornell Law API fails, we report it honestly
                        error_msg = usc_data.get("error", "Failed to retrieve legal text") if usc_data else "API unavailable"
                        regulations[sec] = f"[UNAVAILABLE: {error_msg}] - Real legal text could not be retrieved from Cornell Law School"

            result = {
                "regulation_type": regulation_type,
                "section": section,
                "regulations": regulations,
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "Cornell Legal Information Institute",
                    "total_sections": len(regulations),
                    "status": "success"
                }
            }

            print(f"⚖️  LEGAL API: Retrieved {len(regulations)} real regulation sections")
            return result

        except Exception as e:
            print(f"⚖️  LEGAL API: Regulation search failed - {str(e)}")
            logger.error(f"Legal regulation search failed: {e}")
            return {
                "regulation_type": regulation_type,
                "section": section,
                "regulations": {},
                "error": str(e),
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "Cornell Legal Information Institute",
                    "status": "error"
                }
            }

    # ⚠️  REMOVED: _get_fallback_usc_text() function contained fake legal text
    # This was deceptive - presenting hardcoded text as real legal information
    # When Cornell Law API fails, we now honestly report the failure instead of using fake data

    async def close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()
            self.session = None


class HTTPSearchTool:
    """
    Main HTTP search tool coordinating real API clients.
    """

    def __init__(self):
        self.patent_client = PatentAPIClient()
        self.legal_client = LegalAPIClient()

    async def search_patents_online(
        self,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search for real patents using USPTO API."""
        return await self.patent_client.search_patents(query, limit)

    async def search_legal_regulations(
        self,
        regulation_type: str = "35USC",
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for real legal regulations."""
        return await self.legal_client.search_regulations(regulation_type, section)

    async def close_session(self):
        """Close all HTTP sessions."""
        await self.patent_client.close_session()
        await self.legal_client.close_session()


# Singleton instance for reuse
http_search_tool = HTTPSearchTool()
