"""
DeepWiki MCP Integration for PhD Research Assistant
Enables indexing and searching paper codebases through DeepWiki
"""

import asyncio
import os
from typing import Dict, Any, List, Optional, Union
import requests
import json
from datetime import datetime
import re
from urllib.parse import urlparse, quote


class DeepWikiMCPIntegration:
    """DeepWiki MCP integration for indexing and searching paper codebases"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepWiki MCP integration

        Args:
            api_key: Optional API key for authenticated access (for private repos)
        """
        self.api_key = api_key or os.getenv('DEEPWIKI_API_KEY')
        self.base_url = 'https://mcp.deepwiki.com'
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.api_key:
            self.headers['x-mcp-deepwiki-authorization'] = f'Basic {self.api_key}'

        # Configuration
        self.max_concurrency = int(os.getenv('DEEPWIKI_MAX_CONCURRENCY', '5'))
        self.request_timeout = int(os.getenv('DEEPWIKI_REQUEST_TIMEOUT', '30000'))
        self.max_retries = int(os.getenv('DEEPWIKI_MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('DEEPWIKI_RETRY_DELAY', '250'))

        # Cache for indexed repositories
        self.indexed_repos = {}

    async def index_paper_codebase(self, github_url: str, paper_title: Optional[str] = None,
                                  authors: Optional[List[str]] = None,
                                  year: Optional[int] = None) -> Dict[str, Any]:
        """
        Index a paper's codebase from GitHub using DeepWiki

        Args:
            github_url: GitHub repository URL
            paper_title: Optional title of the paper
            authors: Optional list of paper authors
            year: Optional publication year

        Returns:
            Dictionary with indexing results and metadata
        """
        try:
            # Parse GitHub URL
            parsed_url = urlparse(github_url)
            if 'github.com' not in parsed_url.netloc:
                return {"error": "Invalid GitHub URL"}

            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) < 2:
                return {"error": "Invalid GitHub repository URL format"}

            owner = path_parts[0]
            repo = path_parts[1]

            # Generate DeepWiki URL
            deepwiki_url = f"https://deepwiki.com/{owner}/{repo}"

            # Fetch repository documentation structure
            structure_result = await self._read_wiki_structure(deepwiki_url)

            # Fetch repository contents
            contents_result = await self._read_wiki_contents(deepwiki_url)

            # Store in cache with metadata
            cache_key = f"{owner}/{repo}"
            self.indexed_repos[cache_key] = {
                'github_url': github_url,
                'deepwiki_url': deepwiki_url,
                'paper_title': paper_title,
                'authors': authors,
                'year': year,
                'indexed_at': datetime.now().isoformat(),
                'structure': structure_result,
                'contents': contents_result
            }

            return {
                'status': 'success',
                'repository': cache_key,
                'deepwiki_url': deepwiki_url,
                'paper_metadata': {
                    'title': paper_title,
                    'authors': authors,
                    'year': year
                },
                'documentation': {
                    'pages_indexed': len(structure_result.get('pages', [])) if structure_result else 0,
                    'has_readme': any(p.get('path', '').lower() == 'readme.md'
                                     for p in structure_result.get('pages', [])) if structure_result else False,
                    'has_docs': any('doc' in p.get('path', '').lower()
                                   for p in structure_result.get('pages', [])) if structure_result else False
                }
            }

        except Exception as e:
            return {"error": f"Error indexing codebase: {str(e)}"}

    async def _read_wiki_structure(self, deepwiki_url: str) -> Dict[str, Any]:
        """Read the documentation structure from DeepWiki"""
        try:
            # SSE endpoint for structure reading
            endpoint = f"{self.base_url}/sse"

            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "read_wiki_structure",
                    "arguments": {
                        "url": deepwiki_url
                    }
                },
                "id": "structure_read"
            }

            response = requests.post(
                endpoint,
                headers=self.headers,
                json=request_data,
                timeout=self.request_timeout / 1000
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to read structure: {response.status_code}"}

        except Exception as e:
            return {"error": f"Error reading wiki structure: {str(e)}"}

    async def _read_wiki_contents(self, deepwiki_url: str, mode: str = "aggregate") -> Dict[str, Any]:
        """Read the documentation contents from DeepWiki"""
        try:
            # SSE endpoint for content reading
            endpoint = f"{self.base_url}/sse"

            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "read_wiki_contents",
                    "arguments": {
                        "url": deepwiki_url,
                        "mode": mode
                    }
                },
                "id": "content_read"
            }

            response = requests.post(
                endpoint,
                headers=self.headers,
                json=request_data,
                timeout=self.request_timeout / 1000
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to read contents: {response.status_code}"}

        except Exception as e:
            return {"error": f"Error reading wiki contents: {str(e)}"}

    async def ask_about_codebase(self, repository: str, question: str) -> Dict[str, Any]:
        """
        Ask a question about an indexed codebase

        Args:
            repository: Repository in format "owner/repo"
            question: Question about the codebase

        Returns:
            AI-powered response grounded in the repository context
        """
        try:
            # Check if repository is indexed
            if repository not in self.indexed_repos:
                # Try to generate DeepWiki URL
                deepwiki_url = f"https://deepwiki.com/{repository}"
            else:
                deepwiki_url = self.indexed_repos[repository]['deepwiki_url']

            # Use the ask_question tool
            endpoint = f"{self.base_url}/sse"

            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ask_question",
                    "arguments": {
                        "url": deepwiki_url,
                        "question": question
                    }
                },
                "id": "ask_question"
            }

            response = requests.post(
                endpoint,
                headers=self.headers,
                json=request_data,
                timeout=self.request_timeout / 1000
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'status': 'success',
                    'repository': repository,
                    'question': question,
                    'answer': result.get('result', {}).get('content', 'No answer available'),
                    'sources': result.get('result', {}).get('sources', [])
                }
            else:
                return {"error": f"Failed to get answer: {response.status_code}"}

        except Exception as e:
            return {"error": f"Error asking about codebase: {str(e)}"}

    async def search_codebase(self, repository: str, query: str) -> List[Dict[str, Any]]:
        """
        Search within an indexed codebase

        Args:
            repository: Repository in format "owner/repo"
            query: Search query

        Returns:
            List of search results with file paths and content snippets
        """
        try:
            if repository not in self.indexed_repos:
                return [{"error": f"Repository {repository} not indexed. Please index it first."}]

            contents = self.indexed_repos[repository].get('contents', {})
            results = []

            # Search through contents
            if isinstance(contents, dict):
                # If contents is in pages format
                pages = contents.get('pages', [])
                for page in pages:
                    content = page.get('content', '')
                    if query.lower() in content.lower():
                        # Find matching lines
                        lines = content.split('\n')
                        matching_lines = []
                        for i, line in enumerate(lines, 1):
                            if query.lower() in line.lower():
                                matching_lines.append({
                                    'line': i,
                                    'content': line.strip()
                                })

                        results.append({
                            'path': page.get('path', 'Unknown'),
                            'matches': matching_lines[:5]  # Limit to first 5 matches
                        })

            return results

        except Exception as e:
            return [{"error": f"Error searching codebase: {str(e)}"}]

    async def batch_index_papers(self, paper_repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Index multiple paper repositories in batch

        Args:
            paper_repos: List of dictionaries with github_url, paper_title, authors, year

        Returns:
            Summary of indexing results
        """
        results = {
            'total': len(paper_repos),
            'successful': 0,
            'failed': 0,
            'repositories': []
        }

        for paper_info in paper_repos:
            result = await self.index_paper_codebase(
                github_url=paper_info.get('github_url'),
                paper_title=paper_info.get('paper_title'),
                authors=paper_info.get('authors'),
                year=paper_info.get('year')
            )

            if result.get('status') == 'success':
                results['successful'] += 1
            else:
                results['failed'] += 1

            results['repositories'].append({
                'url': paper_info.get('github_url'),
                'title': paper_info.get('paper_title'),
                'result': result
            })

            # Add delay to respect rate limits
            await asyncio.sleep(1)

        return results

    def get_indexed_repositories(self) -> List[Dict[str, Any]]:
        """Get list of all indexed repositories with metadata"""
        repos = []
        for key, data in self.indexed_repos.items():
            repos.append({
                'repository': key,
                'paper_title': data.get('paper_title'),
                'authors': data.get('authors'),
                'year': data.get('year'),
                'indexed_at': data.get('indexed_at'),
                'github_url': data.get('github_url'),
                'deepwiki_url': data.get('deepwiki_url')
            })
        return repos

    def clear_cache(self, repository: Optional[str] = None):
        """Clear cached indexed repositories"""
        if repository:
            if repository in self.indexed_repos:
                del self.indexed_repos[repository]
                return f"Cleared cache for {repository}"
            return f"Repository {repository} not found in cache"
        else:
            self.indexed_repos.clear()
            return "Cleared all cached repositories"


# Example usage for testing
async def test_deepwiki_integration():
    """Test the DeepWiki integration"""

    # Initialize the integration
    deepwiki = DeepWikiMCPIntegration()

    # Test indexing a paper's codebase
    print("Testing paper codebase indexing...")

    # Example: Index a machine learning paper's repository
    result = await deepwiki.index_paper_codebase(
        github_url="https://github.com/openai/gpt-2",
        paper_title="Language Models are Unsupervised Multitask Learners",
        authors=["Alec Radford", "Jeffrey Wu", "Rewon Child", "David Luan", "Dario Amodei", "Ilya Sutskever"],
        year=2019
    )

    print("Indexing result:", json.dumps(result, indent=2))

    # Test asking a question about the codebase
    if result.get('status') == 'success':
        repo_name = result['repository']

        question_result = await deepwiki.ask_about_codebase(
            repository=repo_name,
            question="What is the main architecture of this model?"
        )

        print("\nQuestion result:", json.dumps(question_result, indent=2))

        # Test searching within the codebase
        search_result = await deepwiki.search_codebase(
            repository=repo_name,
            query="transformer"
        )

        print("\nSearch result:", json.dumps(search_result, indent=2))

    # Show all indexed repositories
    indexed = deepwiki.get_indexed_repositories()
    print("\nIndexed repositories:", json.dumps(indexed, indent=2))


if __name__ == "__main__":
    asyncio.run(test_deepwiki_integration())