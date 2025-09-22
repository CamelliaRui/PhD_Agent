"""
Academic paper search and retrieval module using multiple sources
"""

import asyncio
import requests
from typing import List, Dict, Any
import xml.etree.ElementTree as ET
from urllib.parse import quote


class PaperSearcher:
    """Handles searching and retrieving academic papers from multiple sources"""
    
    def __init__(self):
        self.sources = {
            'arxiv': self._search_arxiv,
            'pubmed': self._search_pubmed,
            'semantic_scholar': self._search_semantic_scholar
        }
    
    async def search_papers(self, query: str, sources: List[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for papers across multiple academic databases
        
        Args:
            query: Search query string
            sources: List of sources to search ('arxiv', 'pubmed', 'semantic_scholar')
            max_results: Maximum number of results per source
            
        Returns:
            List of paper dictionaries with metadata
        """
        if sources is None:
            sources = ['arxiv', 'semantic_scholar']
        
        all_papers = []
        
        # Search each source concurrently
        tasks = []
        for source in sources:
            if source in self.sources:
                tasks.append(self.sources[source](query, max_results))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_papers.extend(result)
                elif isinstance(result, Exception):
                    print(f"Error in paper search: {result}")
        
        # Remove duplicates and sort by relevance
        unique_papers = self._deduplicate_papers(all_papers)
        return unique_papers[:max_results]
    
    async def _search_arxiv(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search arXiv for papers"""
        try:
            encoded_query = quote(query)
            url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={max_results}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            papers = []
            
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                paper = {
                    'source': 'arxiv',
                    'title': entry.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                    'authors': [author.find('{http://www.w3.org/2005/Atom}name').text 
                               for author in entry.findall('{http://www.w3.org/2005/Atom}author')],
                    'abstract': entry.find('{http://www.w3.org/2005/Atom}summary').text.strip(),
                    'url': entry.find('{http://www.w3.org/2005/Atom}id').text,
                    'published': entry.find('{http://www.w3.org/2005/Atom}published').text,
                    'categories': [cat.get('term') for cat in entry.findall('{http://arxiv.org/schemas/atom}primary_category')]
                }
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"Error searching arXiv: {e}")
            return []
    
    async def _search_pubmed(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search PubMed for papers (requires NCBI API)"""
        # This would require NCBI E-utilities API
        # For now, return empty list as it needs API key setup
        return []
    
    async def _search_semantic_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Semantic Scholar API for papers"""
        try:
            encoded_query = quote(query)
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded_query}&limit={max_results}"
            
            headers = {
                'User-Agent': 'PhD-Agent/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for item in data.get('data', []):
                paper = {
                    'source': 'semantic_scholar',
                    'title': item.get('title', ''),
                    'authors': [author.get('name', '') for author in item.get('authors', [])],
                    'abstract': item.get('abstract', ''),
                    'url': item.get('url', ''),
                    'published': item.get('year', ''),
                    'citation_count': item.get('citationCount', 0),
                    'venue': item.get('venue', ''),
                    'paper_id': item.get('paperId', '')
                }
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"Error searching Semantic Scholar: {e}")
            return []
    
    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity"""
        unique_papers = []
        seen_titles = set()
        
        for paper in papers:
            title_normalized = paper.get('title', '').lower().strip()
            if title_normalized and title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_papers.append(paper)
        
        return unique_papers
    
    async def get_paper_details(self, paper_id: str, source: str) -> Dict[str, Any]:
        """Get detailed information about a specific paper"""
        if source == 'semantic_scholar':
            try:
                url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error getting paper details: {e}")
                return {}
        
        return {}


# Example usage
async def main():
    searcher = PaperSearcher()
    papers = await searcher.search_papers("machine learning interpretability", max_results=5)
    
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.get('title', 'No title')}")
        print(f"   Authors: {', '.join(paper.get('authors', []))}")
        print(f"   Source: {paper.get('source', 'Unknown')}")
        print(f"   Abstract: {paper.get('abstract', 'No abstract')[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())