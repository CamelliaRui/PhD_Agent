#!/usr/bin/env python3
"""
Demo script for testing the ReAct agent with simple research tools.

This demonstrates:
1. Tool registration
2. ReAct reasoning loop
3. Observable decision-making traces
4. Task completion assessment
"""

import os
from dotenv import load_dotenv
from core.react_agent import ReactAgent
from typing import List, Dict, Any

load_dotenv()


# Define simple tools for the agent to use
def search_papers(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search for academic papers on a given topic.
    Returns a list of paper titles and abstracts.
    """
    # Simulated paper search results
    papers = {
        "fine-mapping": [
            {
                "title": "Statistical fine-mapping of causal variants in genome-wide association studies",
                "abstract": "We present a Bayesian approach for fine-mapping causal variants using summary statistics...",
                "year": "2024"
            },
            {
                "title": "SuSiE: Sum of Single Effects for fine-mapping",
                "abstract": "A method that enables genome-wide scan for multiple causal variants at each locus...",
                "year": "2023"
            }
        ],
        "transformers": [
            {
                "title": "Attention Is All You Need",
                "abstract": "We propose a new network architecture, the Transformer, based solely on attention mechanisms...",
                "year": "2017"
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "abstract": "We introduce BERT, designed to pre-train deep bidirectional representations...",
                "year": "2019"
            }
        ],
        "crispr": [
            {
                "title": "CRISPR-Cas9 genome editing for functional genomics",
                "abstract": "CRISPR-Cas9 has revolutionized genome editing, enabling precise modifications...",
                "year": "2023"
            }
        ]
    }

    # Simple keyword matching
    query_lower = query.lower()
    results = []

    for topic, topic_papers in papers.items():
        if topic in query_lower:
            results.extend(topic_papers[:max_results])

    if not results:
        # Default results if no match
        results = papers["transformers"][:max_results]

    return results


def summarize_paper(title: str) -> str:
    """
    Get a detailed summary of a paper by its title.
    Returns key findings and methodology.
    """
    # Simulated paper summaries
    summaries = {
        "attention is all you need": """
        Key Findings:
        - Introduced the Transformer architecture based purely on self-attention mechanisms
        - Achieved SOTA results on machine translation tasks
        - Eliminated the need for recurrence and convolutions

        Methodology:
        - Multi-head self-attention layers
        - Positional encodings for sequence order
        - Feed-forward networks in encoder-decoder structure

        Impact: Foundation for BERT, GPT, and modern LLMs
        """,

        "statistical fine-mapping": """
        Key Findings:
        - Bayesian framework for identifying causal variants from GWAS
        - Improves precision over traditional association tests
        - Handles linkage disequilibrium effectively

        Methodology:
        - Prior probabilities based on functional annotations
        - Posterior inference using variational methods
        - Credible sets for multiple causal variants

        Impact: Widely used in post-GWAS analysis
        """
    }

    title_lower = title.lower()
    for key, summary in summaries.items():
        if key in title_lower:
            return summary

    return f"Summary not available for '{title}'. Paper appears to be in the database."


def check_citation_count(title: str) -> int:
    """
    Get the citation count for a paper by title.
    Returns the number of citations.
    """
    # Simulated citation counts
    citations = {
        "attention is all you need": 89000,
        "bert": 67000,
        "statistical fine-mapping": 1200,
        "susie": 450,
        "crispr": 3500
    }

    title_lower = title.lower()
    for key, count in citations.items():
        if key in title_lower:
            return count

    return 0


def main():
    """Run demo tasks with the ReAct agent"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        return

    # Register tools
    tools = {
        "search_papers": search_papers,
        "summarize_paper": summarize_paper,
        "check_citation_count": check_citation_count
    }

    # Create agent
    agent = ReactAgent(
        api_key=api_key,
        tools=tools,
        max_steps=8,
        verbose=True
    )

    print("\n" + "="*70)
    print("🧪 REACT AGENT DEMO")
    print("="*70)

    # Demo Task 1: Simple paper search
    print("\n\n📋 DEMO TASK 1: Find and summarize top transformer papers\n")
    result1 = agent.run(
        "Find papers about transformers in NLP and tell me the most cited one"
    )

    print("\n" + "="*70)
    print("📊 TASK 1 RESULTS")
    print("="*70)
    print(f"Status: {result1['status']}")
    print(f"Steps taken: {result1['steps_taken']}")
    print(f"Final result: {result1['final_result']}")

    # Demo Task 2: More complex multi-step task
    print("\n\n📋 DEMO TASK 2: Research fine-mapping methods\n")
    result2 = agent.run(
        "Find papers on statistical fine-mapping, get a summary of the key findings, and tell me how many citations the main paper has"
    )

    print("\n" + "="*70)
    print("📊 TASK 2 RESULTS")
    print("="*70)
    print(f"Status: {result2['status']}")
    print(f"Steps taken: {result2['steps_taken']}")
    print(f"Final result: {result2['final_result']}")

    # Show full reasoning trace for task 2
    print("\n" + "="*70)
    print("🔍 FULL REASONING TRACE (Task 2)")
    print("="*70)
    print(agent.get_reasoning_trace_text())

    # Save reasoning traces to file
    import json
    with open("react_demo_results.json", "w") as f:
        json.dump({
            "task1": result1,
            "task2": result2
        }, f, indent=2)

    print("\n✅ Results saved to: react_demo_results.json")


if __name__ == "__main__":
    main()
