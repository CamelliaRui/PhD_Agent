"""
Zotero MCP integration for managing research papers and bibliography
"""

import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests
from urllib.parse import urlparse, unquote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZoteroMCPIntegration:
    """Zotero MCP integration for paper management"""

    def __init__(self, api_key: Optional[str] = None, library_id: Optional[str] = None, library_type: str = "user"):
        """
        Initialize Zotero MCP integration

        Args:
            api_key: Zotero API key
            library_id: Zotero library ID (user ID or group ID)
            library_type: Type of library ("user" or "group")
        """
        self.api_key = api_key or os.getenv('ZOTERO_API_KEY')
        self.library_id = library_id or os.getenv('ZOTERO_LIBRARY_ID')
        self.library_type = library_type or os.getenv('ZOTERO_LIBRARY_TYPE', 'user')

        self.base_url = 'https://api.zotero.org'
        self.headers = {
            'Zotero-API-Key': self.api_key,
            'Content-Type': 'application/json'
        } if self.api_key else {}

        # Paper detection patterns
        self.paper_patterns = {
            'arxiv': r'(?:arxiv\.org/(?:abs|pdf)/|arxiv:)(\d{4}\.\d{4,5}(?:v\d+)?)',
            'doi': r'(?:doi\.org/|doi:|DOI:)\s*(10\.\d{4,}/[-._;()/:a-zA-Z0-9]+)',
            'pubmed': r'(?:pubmed\.ncbi\.nlm\.nih\.gov/|PMID:\s*)(\d+)',
            'biorxiv': r'biorxiv\.org/content/(?:10\.\d{4,}/)?(\d{4}\.\d{2}\.\d{2}\.\d+(?:v\d+)?)',
            'medrxiv': r'medrxiv\.org/content/(?:10\.\d{4,}/)?(\d{4}\.\d{2}\.\d{2}\.\d+(?:v\d+)?)',
            'nature': r'nature\.com/articles/(s?\d{5}-[\d-]+)',
            'science': r'science\.org/doi/(10\.\d{4,}/science\.[a-z0-9]+)',
            'cell': r'cell\.com/[^/]+/(?:fulltext|pdf)/([A-Z0-9\(\)-]+)',
            'plos': r'journals\.plos\.org/[^/]+/article\?id=(10\.\d{4,}/journal\.[a-z]+\.\d+)',
            'ieee': r'ieeexplore\.ieee\.org/document/(\d+)',
            'acm': r'dl\.acm\.org/doi/(10\.\d{4,}/\d+(?:\.\d+)*)',
            'springer': r'link\.springer\.com/(?:article|chapter)/(10\.\d{4,}/[^\s]+)',
            'wiley': r'onlinelibrary\.wiley\.com/doi/(?:full|abs|pdf)/(10\.\d{4,}/[^\s]+)',
            'pdf_url': r'(https?://[^\s]+\.pdf)',
            'generic_doi': r'\b(10\.\d{4,}/[-._;()/:a-zA-Z0-9]+)\b'
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test Zotero connection"""
        if not self.api_key or not self.library_id:
            return {"error": "Zotero API key or library ID not configured"}

        try:
            url = f"{self.base_url}/{self.library_type}s/{self.library_id}/collections"
            response = requests.get(url, headers=self.headers, params={'limit': 1})

            if response.status_code == 200:
                return {
                    'status': 'connected',
                    'library_type': self.library_type,
                    'library_id': self.library_id,
                    'collections_accessible': True
                }
            else:
                return {
                    'error': f"Connection failed with status {response.status_code}",
                    'message': response.text
                }

        except Exception as e:
            return {'error': f"Connection test failed: {str(e)}"}

    def extract_paper_references(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract paper references from text (Slack messages, etc.)

        Args:
            text: Text to search for paper references

        Returns:
            List of detected paper references
        """
        papers = []

        # First, handle Slack's URL formatting <URL|display_text>
        # Extract actual URLs from Slack format
        import re
        slack_url_pattern = r'<(https?://[^|>]+)\|?[^>]*>'
        slack_urls = re.findall(slack_url_pattern, text)

        # Also look for direct URLs in the text (not in Slack format)
        direct_url_pattern = r'https?://(?:www\.)?(?:medrxiv|biorxiv|arxiv)\.org/[^\s]+'
        direct_urls = re.findall(direct_url_pattern, text)

        # Add all URLs back to text for processing
        all_urls = slack_urls + direct_urls
        for url in all_urls:
            text = text + " " + url

        # For bioRxiv/medRxiv URLs, add them directly as papers
        for url in all_urls:
            if 'medrxiv.org' in url:
                # Extract DOI from URL
                doi_match = re.search(r'10\.1101/(\d{4}\.\d{2}\.\d{2}\.\d+(?:v\d+)?)', url)
                if doi_match:
                    full_doi = f"10.1101/{doi_match.group(1)}"
                    papers.append({
                        'type': 'medrxiv',
                        'identifier': full_doi,
                        'url': url,
                        'match_text': url
                    })
            elif 'biorxiv.org' in url:
                # Extract DOI from URL
                doi_match = re.search(r'10\.1101/(\d{4}\.\d{2}\.\d{2}\.\d+(?:v\d+)?)', url)
                if doi_match:
                    full_doi = f"10.1101/{doi_match.group(1)}"
                    papers.append({
                        'type': 'biorxiv',
                        'identifier': full_doi,
                        'url': url,
                        'match_text': url
                    })

        # Check for arXiv papers
        for match in re.finditer(self.paper_patterns['arxiv'], text, re.IGNORECASE):
            papers.append({
                'type': 'arxiv',
                'identifier': match.group(1),
                'url': f"https://arxiv.org/abs/{match.group(1)}",
                'match_text': match.group(0)
            })

        # Check for DOIs
        for pattern_name in ['doi', 'generic_doi']:
            for match in re.finditer(self.paper_patterns[pattern_name], text, re.IGNORECASE):
                doi = match.group(1)

                # Check if this DOI is actually from bioRxiv/medRxiv by looking at context
                if doi.startswith('10.1101/'):
                    # This is a bioRxiv/medRxiv DOI, determine which one from context
                    context_text = text[max(0, match.start()-50):match.end()+50].lower()
                    if 'medrxiv' in context_text:
                        # It's a medRxiv paper
                        clean_doi = re.sub(r'v\d+$', '', doi)
                        papers.append({
                            'type': 'medrxiv',
                            'identifier': doi,
                            'url': f"https://www.medrxiv.org/content/{clean_doi}",
                            'match_text': match.group(0)
                        })
                        continue
                    elif 'biorxiv' in context_text:
                        # It's a bioRxiv paper
                        clean_doi = re.sub(r'v\d+$', '', doi)
                        papers.append({
                            'type': 'biorxiv',
                            'identifier': doi,
                            'url': f"https://www.biorxiv.org/content/{clean_doi}",
                            'match_text': match.group(0)
                        })
                        continue

                # Regular DOI handling
                clean_doi = re.sub(r'v\d+$', '', doi)
                papers.append({
                    'type': 'doi',
                    'identifier': doi,  # Keep original for metadata lookup
                    'url': f"https://doi.org/{clean_doi}",  # Use clean DOI for URL
                    'match_text': match.group(0)
                })

        # Check for PubMed
        for match in re.finditer(self.paper_patterns['pubmed'], text, re.IGNORECASE):
            papers.append({
                'type': 'pubmed',
                'identifier': match.group(1),
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{match.group(1)}",
                'match_text': match.group(0)
            })

        # Check for bioRxiv/medRxiv
        for preprint in ['biorxiv', 'medrxiv']:
            for match in re.finditer(self.paper_patterns[preprint], text, re.IGNORECASE):
                identifier = match.group(1)

                # For medRxiv/bioRxiv, the URL needs the full DOI format
                if identifier.startswith('10.1101/'):
                    # Already has full DOI format
                    clean_identifier = re.sub(r'v\d+$', '', identifier)  # Remove version
                    url = f"https://www.{preprint}.org/content/{clean_identifier}"
                else:
                    # Just the paper ID, add the DOI prefix
                    clean_identifier = re.sub(r'v\d+$', '', identifier)  # Remove version
                    url = f"https://www.{preprint}.org/content/10.1101/{clean_identifier}"

                papers.append({
                    'type': preprint,
                    'identifier': identifier,
                    'url': url,
                    'match_text': match.group(0)
                })

        # Check for direct PDF URLs
        for match in re.finditer(self.paper_patterns['pdf_url'], text, re.IGNORECASE):
            url = match.group(1)
            if not any(p['url'] == url for p in papers):  # Avoid duplicates
                papers.append({
                    'type': 'pdf',
                    'identifier': url,
                    'url': url,
                    'match_text': match.group(0)
                })

        # Check for journal-specific patterns
        for journal in ['nature', 'science', 'cell', 'plos', 'ieee', 'acm', 'springer', 'wiley']:
            for match in re.finditer(self.paper_patterns[journal], text, re.IGNORECASE):
                papers.append({
                    'type': journal,
                    'identifier': match.group(1),
                    'url': match.group(0) if 'http' in match.group(0) else None,
                    'match_text': match.group(0)
                })

        # Remove duplicates based on URL and DOI
        seen_identifiers = set()
        unique_papers = []
        for paper in papers:
            # Create identifier based on DOI or URL
            if paper.get('identifier'):
                # Clean identifier for comparison
                clean_id = re.sub(r'v\d+$', '', paper['identifier'])
                identifier = f"{paper['type']}:{clean_id}"
            else:
                identifier = f"{paper['type']}:{paper['url']}"

            if identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                unique_papers.append(paper)

        return unique_papers

    async def fetch_paper_metadata(self, paper_ref: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch metadata for a paper reference

        Args:
            paper_ref: Paper reference dictionary from extract_paper_references

        Returns:
            Paper metadata
        """
        metadata = {
            'title': None,
            'authors': [],
            'abstract': None,
            'year': None,
            'journal': None,
            'doi': None,
            'url': paper_ref['url'],
            'type': paper_ref['type']
        }

        try:
            if paper_ref['type'] == 'arxiv':
                # Fetch arXiv metadata
                arxiv_id = paper_ref['identifier']
                api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
                response = requests.get(api_url)

                if response.status_code == 200:
                    # Parse arXiv XML response
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)

                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    entry = root.find('.//atom:entry', ns)

                    if entry:
                        metadata['title'] = entry.find('atom:title', ns).text.strip()
                        metadata['abstract'] = entry.find('atom:summary', ns).text.strip()

                        authors = []
                        for author in entry.findall('atom:author', ns):
                            name = author.find('atom:name', ns).text
                            authors.append(name)
                        metadata['authors'] = authors

                        published = entry.find('atom:published', ns).text
                        metadata['year'] = published[:4] if published else None
                        metadata['journal'] = 'arXiv'

            elif paper_ref['type'] in ['biorxiv', 'medrxiv']:
                # For bioRxiv/medRxiv, use CrossRef API with DOI
                doi = paper_ref['identifier']

                # Remove version suffix (v1, v2, etc.) from DOI
                doi = re.sub(r'v\d+$', '', doi)

                if not doi.startswith('10.'):
                    doi = f"10.1101/{doi}"

                api_url = f"https://api.crossref.org/works/{doi}"
                response = requests.get(api_url)

                if response.status_code == 200:
                    data = response.json()['message']

                    # Safely get title
                    title_list = data.get('title', [])
                    metadata['title'] = title_list[0] if title_list else f"Paper from {paper_ref['type']}: {doi}"
                    metadata['doi'] = doi

                    authors = []
                    for author in data.get('author', []):
                        name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                        if name:
                            authors.append(name)
                    metadata['authors'] = authors

                    metadata['abstract'] = data.get('abstract')

                    published = data.get('posted-date') or data.get('published-print') or data.get('published-online')
                    if published and published.get('date-parts'):
                        date_parts = published.get('date-parts', [[]])[0]
                        if date_parts:
                            metadata['year'] = str(date_parts[0])

                    metadata['journal'] = paper_ref['type'].capitalize()

            elif paper_ref['type'] == 'doi':
                # Fetch DOI metadata from CrossRef
                doi = paper_ref['identifier']

                # Remove version suffix (v1, v2, etc.) from DOI if present
                doi = re.sub(r'v\d+$', '', doi)

                api_url = f"https://api.crossref.org/works/{doi}"
                response = requests.get(api_url)

                if response.status_code == 200:
                    data = response.json()['message']

                    # Safely get title
                    title_list = data.get('title', [])
                    metadata['title'] = title_list[0] if title_list else f"Paper from DOI: {doi}"
                    metadata['doi'] = doi

                    authors = []
                    for author in data.get('author', []):
                        name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                        if name:
                            authors.append(name)
                    metadata['authors'] = authors

                    metadata['abstract'] = data.get('abstract')

                    published = data.get('published-print') or data.get('published-online')
                    if published and published.get('date-parts'):
                        date_parts = published.get('date-parts', [[]])[0]
                        if date_parts:
                            metadata['year'] = str(date_parts[0])

                    # Safely get journal title
                    journal_list = data.get('container-title', [])
                    metadata['journal'] = journal_list[0] if journal_list else None

            elif paper_ref['type'] == 'pubmed':
                # Fetch PubMed metadata
                pmid = paper_ref['identifier']
                api_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                params = {
                    'db': 'pubmed',
                    'id': pmid,
                    'retmode': 'json'
                }
                response = requests.get(api_url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and pmid in data['result']:
                        article = data['result'][pmid]

                        metadata['title'] = article.get('title')

                        authors = []
                        for author in article.get('authors', []):
                            authors.append(author.get('name'))
                        metadata['authors'] = authors

                        metadata['year'] = article.get('pubdate', '').split()[0]
                        metadata['journal'] = article.get('source')
                        metadata['doi'] = article.get('doi')

        except Exception as e:
            logger.error(f"Error fetching metadata for {paper_ref['type']}: {e}")

        # Set title to URL if no metadata found
        if not metadata['title']:
            metadata['title'] = f"Paper from {paper_ref['type']}: {paper_ref['identifier']}"

        return metadata

    async def add_to_zotero(self, paper_metadata: Dict[str, Any], collection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a paper to Zotero library

        Args:
            paper_metadata: Paper metadata from fetch_paper_metadata
            collection_id: Optional Zotero collection ID

        Returns:
            Result of the addition
        """
        if not self.api_key or not self.library_id:
            return {"error": "Zotero not configured"}

        try:
            # Prepare Zotero item
            item = {
                "itemType": "journalArticle",
                "title": paper_metadata.get('title', ''),
                "creators": [
                    {"creatorType": "author", "name": author}
                    for author in paper_metadata.get('authors', [])
                ],
                "abstractNote": paper_metadata.get('abstract', ''),
                "date": paper_metadata.get('year', ''),
                "publicationTitle": paper_metadata.get('journal', ''),
                "DOI": paper_metadata.get('doi', ''),
                "url": paper_metadata.get('url', ''),
                "accessDate": datetime.now().strftime("%Y-%m-%d"),
                "tags": [
                    {"tag": "from-slack"},
                    {"tag": paper_metadata.get('type', 'paper')}
                ]
            }

            # Add to collection if specified
            if collection_id:
                item["collections"] = [collection_id]

            # Create item in Zotero
            url = f"{self.base_url}/{self.library_type}s/{self.library_id}/items"
            response = requests.post(
                url,
                headers=self.headers,
                json=[item]
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    'success': True,
                    'key': result['successful']['0']['key'] if 'successful' in result else 'unknown',
                    'title': paper_metadata.get('title'),
                    'message': 'Paper added to Zotero successfully'
                }
            else:
                return {
                    'error': f"Failed to add to Zotero: {response.status_code}",
                    'message': response.text
                }

        except Exception as e:
            return {'error': f"Error adding to Zotero: {str(e)}"}

    async def search_library(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Zotero library

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching items
        """
        if not self.api_key or not self.library_id:
            return []

        try:
            url = f"{self.base_url}/{self.library_type}s/{self.library_id}/items"
            params = {
                'q': query,
                'limit': limit,
                'format': 'json'
            }

            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                items = response.json()

                results = []
                for item in items:
                    data = item.get('data', {})
                    results.append({
                        'key': data.get('key'),
                        'title': data.get('title'),
                        'creators': data.get('creators', []),
                        'year': data.get('date'),
                        'itemType': data.get('itemType'),
                        'doi': data.get('DOI'),
                        'url': data.get('url')
                    })

                return results

            return []

        except Exception as e:
            logger.error(f"Error searching Zotero: {e}")
            return []

    async def get_collections(self) -> List[Dict[str, str]]:
        """
        Get all collections in the library

        Returns:
            List of collections
        """
        if not self.api_key or not self.library_id:
            return []

        try:
            url = f"{self.base_url}/{self.library_type}s/{self.library_id}/collections"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                collections = response.json()

                return [
                    {
                        'key': col['data']['key'],
                        'name': col['data']['name'],
                        'parent': col['data'].get('parentCollection')
                    }
                    for col in collections
                ]

            return []

        except Exception as e:
            logger.error(f"Error getting collections: {e}")
            return []

    async def check_if_exists(self, identifier: str, identifier_type: str = 'doi') -> bool:
        """
        Check if a paper already exists in Zotero

        Args:
            identifier: Paper identifier (DOI, URL, etc.)
            identifier_type: Type of identifier

        Returns:
            True if exists, False otherwise
        """
        if not self.api_key or not self.library_id:
            return False

        try:
            # Search by identifier
            if identifier_type == 'doi':
                results = await self.search_library(identifier)
                return any(item.get('doi') == identifier for item in results)
            elif identifier_type == 'url':
                results = await self.search_library(identifier)
                return any(item.get('url') == identifier for item in results)
            else:
                results = await self.search_library(identifier)
                return len(results) > 0

        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            return False


# Example usage
async def main():
    """Test Zotero integration"""

    zotero = ZoteroMCPIntegration()

    # Test connection
    connection = await zotero.test_connection()
    print(f"Connection: {json.dumps(connection, indent=2)}")

    # Test paper extraction
    test_text = """
    Check out this interesting paper on arXiv: https://arxiv.org/abs/2301.12345
    Also, there's a great Nature paper: https://doi.org/10.1038/s41586-023-12345-6
    And a PubMed article: https://pubmed.ncbi.nlm.nih.gov/12345678/
    """

    papers = zotero.extract_paper_references(test_text)
    print(f"\nExtracted papers: {json.dumps(papers, indent=2)}")

    # Test metadata fetching
    if papers:
        metadata = await zotero.fetch_paper_metadata(papers[0])
        print(f"\nMetadata: {json.dumps(metadata, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())