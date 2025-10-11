#!/usr/bin/env python3
"""
Run conference planner with interests provided as arguments
Usage: python run_conference_planner.py "interest 1" "interest 2" "interest 3"
"""

import sys
import asyncio
from conference_planner import ConferencePlanner
from pathlib import Path

async def run_planner(research_interests):
    """Run the conference planner with provided interests"""

    print("\n" + "="*70)
    print("🎉 ASHG 2025 CONFERENCE PLANNER")
    print("="*70 + "\n")

    # Setup paths
    conference_name = "ASHG2025"
    conference_dir = Path("/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025")
    pdf_path = conference_dir / "ASHG-2025-Annual-Meeting-Abstracts.pdf"

    # Initialize planner
    print(f"📚 Initializing conference planner...")
    planner = ConferencePlanner(
        conference_name=conference_name,
        conference_dir=str(conference_dir)
    )

    # Parse PDF
    print(f"\n📄 Parsing conference PDF...")
    talks = planner.parse_conference_pdf(str(pdf_path))

    if not talks:
        print("❌ No talks found!")
        return

    print(f"✅ Parsed {len(talks)} talks!\n")

    # Show sample
    print("📋 Sample talks:")
    for i, talk in enumerate(talks[:3], 1):
        print(f"  {i}. {talk.title[:60]}...")
        print(f"     {talk.day or 'TBD'} at {talk.time or 'TBD'}")
    print()

    # Set research interests
    planner.research_interests = research_interests
    print("🎯 Your research interests:")
    for i, interest in enumerate(research_interests, 1):
        print(f"  {i}. {interest}")
    print()

    # Save interests
    interests_file = Path.cwd() / "research_interests.md"
    planner.save_research_interests(str(interests_file))

    # Index talks
    print("🔍 Indexing talks with ChromaDB...")
    print("   (This may take 2-3 minutes for 300+ talks...)")
    planner.index_talks()
    print("✅ Indexing complete!\n")

    # Find relevant talks
    print("🎯 Finding relevant talks...")
    relevant_talks = planner.find_relevant_talks(
        top_k=50,
        min_relevance_score=0.3
    )

    if not relevant_talks:
        print("❌ No relevant talks found.")
        return

    print(f"✅ Found {len(relevant_talks)} relevant talks!\n")

    # Show top 5
    print("🌟 Top 5 most relevant talks:")
    for i, (talk, score) in enumerate(relevant_talks[:5], 1):
        print(f"\n  {i}. [{score:.1%}] {talk.title}")
        print(f"     {talk.day or 'TBD'} at {talk.time or 'TBD'}")
        print(f"     {talk.abstract[:100]}...")

    # Generate schedule
    schedule_file = conference_dir / "ashg_schedule.md"
    print(f"\n📅 Generating schedule...")
    planner.generate_schedule_markdown(
        relevant_talks,
        str(schedule_file)
    )

    # Conflicts
    conflicts = planner.detect_conflicts(relevant_talks)

    # Summary
    print("\n" + "="*70)
    print("🎊 SUCCESS!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   Total talks: {len(talks)}")
    print(f"   Relevant talks: {len(relevant_talks)}")
    print(f"   Conflicts: {len(conflicts)}")
    print(f"\n📄 Output files:")
    print(f"   📅 Schedule: {schedule_file}")
    print(f"   📚 Interests: {interests_file}")
    print("="*70 + "\n")

if __name__ == "__main__":
    # Get interests from command line or use defaults
    if len(sys.argv) > 1:
        interests = sys.argv[1:]
    else:
        # Default sample interests
        interests = [
            "CRISPR gene editing and therapeutic applications",
            "Cancer genomics and precision medicine",
            "Machine learning for genomic prediction"
        ]
        print("\n⚠️  No interests provided. Using sample interests.")
        print("   Usage: python run_conference_planner.py \"interest 1\" \"interest 2\"\n")

    asyncio.run(run_planner(interests))