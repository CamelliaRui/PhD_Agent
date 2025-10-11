#!/usr/bin/env python3
"""Quick test of exclusion filtering"""

from conference_planner import ConferenceTalk

# Create a mock planner with exclusions
class MockPlanner:
    def __init__(self):
        self.exclusion_topics = [
            "wet-lab protocols and techniques",
            "clinical case studies without methods",
            "traditional genetics without computational aspects"
        ]

# Test talks
talks = [
    ConferenceTalk(
        title="CRISPR protocol optimization for gene editing",
        abstract="We developed a pipetting protocol for western blot and cell culture optimization",
        authors=["John Doe"],
        session_type="talk"
    ),
    ConferenceTalk(
        title="Statistical fine-mapping of eQTLs using Bayesian methods",
        abstract="We developed a novel computational approach using Bayesian inference for statistical fine-mapping",
        authors=["Jane Smith"],
        session_type="talk"
    ),
    ConferenceTalk(
        title="Clinical outcomes in cancer patients",
        abstract="Case series of 50 patients with clinical management and treatment protocol outcomes",
        authors=["Dr. Clinical"],
        session_type="talk"
    ),
]

# Import the method
from conference_planner import ConferencePlanner

planner = ConferencePlanner("TEST", ".")
planner.exclusion_topics = [
    "wet-lab protocols",
    "clinical case studies"
]

print("Testing exclusion filter:\n")
for i, talk in enumerate(talks, 1):
    excluded = planner.should_exclude_talk(talk)
    status = "❌ EXCLUDED" if excluded else "✅ KEPT"
    print(f"{i}. {status}")
    print(f"   Title: {talk.title}")
    print(f"   Abstract: {talk.abstract[:80]}...")
    print()
