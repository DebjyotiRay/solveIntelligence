import httpx
import asyncio
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import hashlib
import time
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PatentAPIClient:
    """Patent API client using SearchAPI.io Google Patents API."""

    def __init__(self):
        self.searchapi_base = "https://www.searchapi.io/api/v1/search"
        self.searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        self.has_searchapi_key = bool(self.searchapi_key)
        
        self.session = None
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 1.0
        
        logger.info(f"Patent API: {'Configured' if self.has_searchapi_key else 'No API key - search disabled'}")

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
        """Search patents using SearchAPI.io Google Patents API."""
        logger.info(f"Patent search: '{query}' (limit={limit})")

        try:
            cache_key = self._get_cache_key(query, {"limit": limit})
            if cache_key in self.cache:
                logger.debug("Using cached patent results")
                return self.cache[cache_key]

            if not self.has_searchapi_key:
                return self._create_error_response(query, "API key required")

            await self._rate_limit()
            session = await self._get_session()

            params = {
                "engine": "google_patents",
                "q": query,
                "num": limit,
                "api_key": self.searchapi_key
            }
            
            start_time = time.time()
            response = await session.get(self.searchapi_base, params=params)
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code != 200:
                raise Exception(f"API returned status {response.status_code}")
            
            data = response.json()
            patents = self._parse_patent_results(data.get("organic_results", []), limit)
            
            result_data = {
                "query": query,
                "total_results": data.get("search_information", {}).get("total_results", len(patents)),
                "patents": patents,
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "SearchAPI.io",
                    "response_time_ms": response_time,
                    "status": "success"
                }
            }
            
            self.cache[cache_key] = result_data
            logger.info(f"Found {len(patents)} patents")
            return result_data

        except Exception as e:
            logger.error(f"Patent search failed: {e}")
            return self._create_error_response(query, str(e))

    def _parse_patent_results(self, results: list, limit: int) -> list:
        """Parse patent results from API response."""
        patents = []
        for result in results[:limit]:
            patent = {
                "patent_id": result.get("result_id", result.get("link", "Unknown")),
                "title": result.get("title", "No title"),
                "abstract": result.get("snippet", "No abstract")[:500],
                "filing_date": result.get("filing_date", "Unknown"),
                "inventors": result.get("inventors", []),
                "assignee": result.get("assignee", "Not specified"),
                "status": result.get("status", "Unknown"),
                "link": result.get("link", "")
            }
            patents.append(patent)
        return patents

    def _create_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "query": query,
            "total_results": 0,
            "patents": [],
            "error": error,
            "search_metadata": {
                "timestamp": datetime.now().isoformat(),
                "api_source": "SearchAPI.io",
                "status": "error"
            }
        }

    async def close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()
            self.session = None


class LegalAPIClient:
    """Legal API client for Cornell Law School's Legal Information Institute."""

    def __init__(self):
        self.base_url = "https://www.law.cornell.edu/uscode/text"
        self.session = None
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 2.0
        
        logger.info("Legal API: Initialized")

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
        """Get USC section text from Cornell LII."""
        logger.info(f"Fetching USC {title} § {section}")

        try:
            cache_key = f"usc_{title}_{section}"
            if cache_key in self.cache:
                logger.debug("Using cached legal text")
                return self.cache[cache_key]

            await self._rate_limit()
            session = await self._get_session()

            url = f"{self.base_url}/{title}/{section}"
            start_time = time.time()
            response = await session.get(url)
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise Exception(f"API returned status {response.status_code}")

            text_content = self._extract_legal_text(response.text)

            result = {
                "title": title,
                "section": section,
                "full_citation": f"{title} U.S.C. § {section}",
                "text": text_content,
                "source": "Cornell LII",
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "Cornell LII",
                    "response_time_ms": response_time,
                    "status": "success"
                }
            }

            self.cache[cache_key] = result
            logger.info(f"Successfully retrieved USC {title} § {section}")
            return result

        except Exception as e:
            logger.error(f"Failed to retrieve USC {title} § {section}: {e}")
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
        soup = BeautifulSoup(html_content, 'html.parser')
        legal_content = soup.find('div', class_='field-item')
        if legal_content:
            return legal_content.get_text(strip=True)
        text = soup.get_text()
        return text[:2000] if text else "Legal text not found"

    async def search_regulations(
        self,
        regulation_type: str = "35USC",
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for legal regulations."""
        logger.info(f"Searching {regulation_type} regulations" + (f" (section {section})" if section else ""))

        try:
            regulations = {}

            if regulation_type == "35USC":
                key_sections = ["101", "102", "103", "112"] if not section else [section]

                for sec in key_sections:
                    usc_data = await self.get_usc_section("35", sec)
                    if usc_data and "error" not in usc_data:
                        regulations[sec] = usc_data["text"]
                    else:
                        error_msg = usc_data.get("error", "Failed to retrieve") if usc_data else "API unavailable"
                        regulations[sec] = f"[UNAVAILABLE: {error_msg}]"

            result = {
                "regulation_type": regulation_type,
                "section": section,
                "regulations": regulations,
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "Cornell LII",
                    "total_sections": len(regulations),
                    "status": "success"
                }
            }

            logger.info(f"Retrieved {len(regulations)} regulation sections")
            return result

        except Exception as e:
            logger.error(f"Regulation search failed: {e}")
            return {
                "regulation_type": regulation_type,
                "section": section,
                "regulations": {},
                "error": str(e),
                "search_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_source": "Cornell LII",
                    "status": "error"
                }
            }

    async def close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()
            self.session = None


class HTTPSearchTool:
    """HTTP search tool coordinating API clients."""

    def __init__(self):
        self.patent_client = PatentAPIClient()
        self.legal_client = LegalAPIClient()

    async def search_patents_online(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for patents using SearchAPI.io."""
        return await self.patent_client.search_patents(query, limit)

    async def search_legal_regulations(
        self, regulation_type: str = "35USC", section: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for legal regulations from Cornell LII."""
        return await self.legal_client.search_regulations(regulation_type, section)

    async def close_session(self):
        """Close all HTTP sessions."""
        await self.patent_client.close_session()
        await self.legal_client.close_session()


# Singleton instance for reuse
http_search_tool = HTTPSearchTool()
