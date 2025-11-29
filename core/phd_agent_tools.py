"""
Tool wrappers for integrating PhD Agent with ReAct agent.

This module provides synchronous wrappers around PhD Agent's async methods,
making them compatible with the ReAct agent's tool registry.
"""

import asyncio
from typing import Dict, Any, List, Callable
import json


class PhdAgentToolWrapper:
    """
    Wraps PhD Agent methods to make them compatible with ReAct agent.

    The ReAct agent expects synchronous callables, but PhD Agent uses async methods.
    This wrapper handles the async/sync conversion.
    """

    def __init__(self, phd_agent):
        """
        Initialize tool wrapper with PhD Agent instance.

        Args:
            phd_agent: Instance of PhdAgent with all the research tools
        """
        self.agent = phd_agent
        self._event_loop = None

    def _run_async(self, coro):
        """Helper to run async coroutines in sync context"""
        try:
            # Try to get running loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context, create new loop
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(coro)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)

    # ==================== Paper Search Tools ====================

    def search_papers(self, query: str, max_results: int = 3) -> str:
        """
        Search for academic papers on a given topic.

        Args:
            query: Search query (e.g., "CRISPR gene editing", "transformer models")
            max_results: Maximum number of papers to return (default: 3)

        Returns:
            JSON string with list of papers (title, authors, abstract, url)
        """
        papers = self._run_async(
            self.agent.search_papers(query, max_results)
        )

        if not papers:
            return json.dumps({"error": "No papers found"})

        # Format for ReAct agent
        result = {
            "count": len(papers),
            "papers": [
                {
                    "title": p.get("title", ""),
                    "authors": p.get("authors", [])[:3],  # First 3 authors
                    "abstract": p.get("abstract", "")[:200] + "...",  # Preview
                    "year": p.get("year", ""),
                    "url": p.get("url", "")
                }
                for p in papers
            ]
        }

        return json.dumps(result, indent=2)

    # ==================== Conference Planning Tools ====================

    def find_conference_talks(self, interests: str, conference: str = "ASHG2025") -> str:
        """
        Find relevant conference talks based on research interests.

        Args:
            interests: Research interests (e.g., "fine-mapping, eQTL analysis")
            conference: Conference name (default: ASHG2025)

        Returns:
            JSON string with relevant talks and relevance scores
        """
        try:
            from pathlib import Path
            from conference_planner import ConferencePlanner

            # Check if conference exists
            conference_dir = Path.cwd() / "conference" / conference
            if not conference_dir.exists():
                return json.dumps({
                    "error": f"Conference {conference} not found",
                    "available": [d.name for d in (Path.cwd() / "conference").iterdir() if d.is_dir()]
                })

            # Initialize planner
            planner = ConferencePlanner(
                conference_name=conference,
                conference_dir=str(conference_dir)
            )

            # Load cached talks
            cache_file = conference_dir / f".{conference.lower()}_talks_cache.pkl"
            if not cache_file.exists():
                return json.dumps({
                    "error": "Conference not parsed yet. Run 'conference plan' first."
                })

            # Set interests
            planner.research_interests = [i.strip() for i in interests.split(",")]

            # Index and search
            planner.index_talks()
            relevant_talks = planner.find_relevant_talks(top_k=5, min_relevance_score=0.3)

            result = {
                "conference": conference,
                "interests": planner.research_interests,
                "count": len(relevant_talks),
                "top_talks": [
                    {
                        "title": talk.get("title", ""),
                        "relevance": f"{talk.get('relevance_score', 0)*100:.1f}%",
                        "day": talk.get("day", ""),
                        "time": talk.get("time", ""),
                        "type": talk.get("type", "")
                    }
                    for talk in relevant_talks[:5]
                ]
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    # ==================== Code Analysis Tools ====================

    def search_paper_code(self, repository: str, query: str) -> str:
        """
        Search within a paper's codebase using DeepWiki.

        Args:
            repository: GitHub repo (e.g., "huggingface/transformers")
            query: Search query (e.g., "attention mechanism implementation")

        Returns:
            JSON string with code snippets and file locations
        """
        results = self._run_async(
            self.agent.search_codebase(repository, query)
        )

        if not results or (isinstance(results, list) and "error" in results[0]):
            return json.dumps({
                "error": "Repository not indexed or search failed",
                "hint": "Use index_paper_codebase tool first"
            })

        # Format results
        formatted = {
            "repository": repository,
            "query": query,
            "matches": []
        }

        for result in results[:3]:  # Top 3 files
            formatted["matches"].append({
                "file": result.get("path", ""),
                "snippets": result.get("matches", [])[:2]  # Top 2 snippets per file
            })

        return json.dumps(formatted, indent=2)

    # ==================== Research Insights Tools ====================

    def brainstorm_research_ideas(self, research_area: str, current_work: str = "") -> str:
        """
        Generate research ideas and suggestions for a given area.

        Args:
            research_area: Area to brainstorm (e.g., "single-cell genomics")
            current_work: Optional description of current work

        Returns:
            Text with brainstormed ideas, questions, and directions
        """
        ideas = self._run_async(
            self.agent.brainstorm_ideas(research_area, current_work)
        )

        return ideas if ideas else "No ideas generated"

    # ==================== Information Retrieval Tools ====================

    def get_research_interests(self) -> str:
        """
        Get the user's current research interests from file.

        Returns:
            JSON string with research interests, authors of interest, exclusions
        """
        try:
            from pathlib import Path

            interests_file = Path.cwd() / "research_interests.md"
            if not interests_file.exists():
                return json.dumps({
                    "error": "No research interests file found",
                    "hint": "Run 'interests update' first"
                })

            # Parse the interests file
            content = interests_file.read_text()

            # Simple parsing (could be enhanced)
            result = {
                "raw_content": content[:500],  # First 500 chars
                "hint": "Research interests are stored in research_interests.md"
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})


def create_phd_agent_tool_registry(phd_agent) -> Dict[str, Callable]:
    """
    Create a tool registry for the ReAct agent from PhD Agent methods.

    Args:
        phd_agent: Instance of PhdAgent

    Returns:
        Dictionary mapping tool names to callable functions
    """
    wrapper = PhdAgentToolWrapper(phd_agent)

    tools = {
        # Paper search and analysis
        "search_papers": wrapper.search_papers,
        "brainstorm_ideas": wrapper.brainstorm_research_ideas,

        # Conference planning
        "find_conference_talks": wrapper.find_conference_talks,

        # Code analysis
        "search_paper_code": wrapper.search_paper_code,

        # Information retrieval
        "get_research_interests": wrapper.get_research_interests,
    }

    return tools


def get_tool_descriptions() -> str:
    """Get human-readable descriptions of all available tools"""
    descriptions = """
Available Research Tools:
========================

📚 Paper Research:
  - search_papers(query, max_results=3)
      Search academic papers on any topic
      Example: search_papers("CRISPR gene editing", 5)

  - brainstorm_ideas(research_area, current_work="")
      Generate research ideas for a given area
      Example: brainstorm_ideas("single-cell genomics")

📅 Conference Planning:
  - find_conference_talks(interests, conference="ASHG2025")
      Find relevant talks at a conference
      Example: find_conference_talks("fine-mapping, eQTL", "ASHG2025")

💻 Code Analysis:
  - search_paper_code(repository, query)
      Search within a paper's codebase
      Example: search_paper_code("huggingface/transformers", "attention")

ℹ️ Information:
  - get_research_interests()
      Retrieve your saved research interests
      Example: get_research_interests()
"""
    return descriptions
