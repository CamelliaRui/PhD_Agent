"""
Quick script to regenerate ASHG schedule without interactive prompts
"""
import asyncio
from conference_planner import ConferencePlanner

async def regenerate():
    # Initialize planner
    planner = ConferencePlanner(
        conference_name="ASHG2025",
        conference_dir="/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025"
    )

    # Parse conference PDF (will use cache)
    print("📄 Loading conference talks...")
    pdf_path = "/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025/ASHG-2025-Annual-Meeting-Abstracts.pdf"
    planner.parse_conference_pdf(pdf_path)

    # Load existing research interests
    print("🎯 Loading research interests...")
    planner.load_research_interests("research_interests.md")
    print(f"   Loaded {len(planner.research_interests)} interests")
    if planner.authors_of_interest:
        print(f"   Loaded {len(planner.authors_of_interest)} authors of interest: {planner.authors_of_interest}")

    # Index talks
    print("🔍 Indexing talks in ChromaDB...")
    planner.index_talks()

    # Find relevant talks
    print("🎯 Finding relevant talks...")
    relevant_talks = planner.find_relevant_talks(top_k=50, min_relevance_score=0.3)
    print(f"   Found {len(relevant_talks)} relevant talks")

    # Generate schedule
    print("📝 Generating schedule...")
    output_path = "/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025/ashg2025_schedule.md"
    planner.generate_schedule_markdown(relevant_talks, output_path)

    print("\n🎉 Schedule regenerated successfully!")
    print(f"   Output: {output_path}")

if __name__ == "__main__":
    asyncio.run(regenerate())
