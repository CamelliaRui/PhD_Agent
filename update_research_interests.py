#!/usr/bin/env python3
"""
Interactive script to capture and save research interests
"""

from pathlib import Path
from datetime import datetime


def update_research_interests():
    """Interactively capture research interests and save to file"""

    print("\n" + "="*70)
    print("🎯 RESEARCH INTERESTS SETUP")
    print("="*70)

    output_file = Path.cwd() / "research_interests.md"

    # Check for existing interests
    existing_interests = []
    if output_file.exists():
        try:
            with open(output_file, 'r') as f:
                content = f.read()

            # Extract existing interests
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('-') and not line.startswith('#'):
                    interest = line.lstrip('- ').strip()
                    if interest and interest.upper() != 'NA':
                        existing_interests.append(interest)

            if existing_interests:
                print("\n📚 Current research interests found:")
                for i, interest in enumerate(existing_interests, 1):
                    print(f"  {i}. {interest}")

                print("\n" + "-"*70)
                choice = input("\nDo you want to (a)dd to these, (r)eplace them, or (k)eep as-is? [a/r/k]: ").strip().lower()
                print("-"*70)

                if choice == 'k':
                    print(f"\n✅ Keeping existing {len(existing_interests)} interests.")
                    print(f"📄 File: {output_file}\n")
                    return
                elif choice == 'r':
                    print("\n🔄 Starting fresh...\n")
                    interests = []
                else:  # default to 'add'
                    print(f"\n➕ Adding to existing {len(existing_interests)} interests...\n")
                    interests = existing_interests.copy()
            else:
                interests = []
        except Exception as e:
            print(f"⚠️  Could not read existing file: {e}")
            interests = []
    else:
        interests = []

    if not interests:
        print("\nLet's capture your research interests for conference planning.")
        print("These will be used to match relevant talks and generate schedules.")
        print("\n💡 Tips:")
        print("  - Be specific about your research areas")
        print("  - Include methodologies you're interested in")
        print("  - Mention specific diseases, organisms, or systems")
        print("  - Include computational/experimental techniques")
        print("\n📝 Examples:")
        print("  - CRISPR gene editing and therapeutic applications")
        print("  - Population genetics and evolutionary genomics")
        print("  - Single-cell RNA sequencing and spatial transcriptomics")
        print("  - Cancer genomics and precision medicine")
        print("  - Deep learning for variant effect prediction")
        print("  - Epigenetics and chromatin accessibility")

    print("\n" + "-"*70)
    print("\nEnter your research interests one per line.")
    print("Type 'done' when finished, or 'clear' to start over.")
    print("-"*70 + "\n")

    while True:
        try:
            # Show current count
            prompt = f"Interest #{len(interests) + 1}: "
            interest = input(prompt).strip()

            if interest.lower() == 'done':
                if not interests:
                    print("\n⚠️  You must enter at least one research interest.")
                    print("   Please continue entering your interests.\n")
                    continue
                break

            if interest.lower() == 'clear':
                interests = []
                print("\n🗑️  Cleared all interests. Starting over...\n")
                continue

            if interest.lower() == 'list':
                if interests:
                    print("\n📋 Current interests:")
                    for i, item in enumerate(interests, 1):
                        print(f"  {i}. {item}")
                    print()
                else:
                    print("\n📋 No interests entered yet.\n")
                continue

            if interest.lower() == 'help':
                print("\n📖 Commands:")
                print("  - Type your interest and press Enter to add it")
                print("  - 'done' - Save and finish")
                print("  - 'list' - Show current interests")
                print("  - 'clear' - Clear all and start over")
                print("  - 'remove N' - Remove interest number N")
                print("  - 'help' - Show this help\n")
                continue

            if interest.lower().startswith('remove '):
                try:
                    idx = int(interest.split()[1]) - 1
                    if 0 <= idx < len(interests):
                        removed = interests.pop(idx)
                        print(f"  ✓ Removed: {removed}\n")
                    else:
                        print(f"  ❌ Invalid index. Use 'list' to see current interests.\n")
                except (ValueError, IndexError):
                    print("  ❌ Usage: remove N (where N is the interest number)\n")
                continue

            if interest:
                interests.append(interest)
                print(f"  ✓ Added: {interest}")
                print(f"  (Total: {len(interests)} interests)\n")

        except EOFError:
            print("\n\n⚠️  Input interrupted. Saving current interests...\n")
            break

        except KeyboardInterrupt:
            print("\n\n⚠️  Cancelled by user.")
            save_anyway = input("\nSave interests entered so far? (y/n): ").strip().lower()
            if save_anyway == 'y' and interests:
                break
            else:
                print("❌ Not saving. Exiting.")
                return

    if not interests:
        print("\n❌ No interests to save. Exiting.")
        return

    # Show summary
    print("\n" + "="*70)
    print("✅ RESEARCH INTERESTS CAPTURED")
    print("="*70)
    print(f"\nYou entered {len(interests)} research interests:\n")
    for i, interest in enumerate(interests, 1):
        print(f"  {i}. {interest}")

    # Confirm save
    print("\n" + "-"*70)
    confirm = input("\nSave these interests to research_interests.md? (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ Not saving. Exiting.")
        return

    # Save to file (output_file already defined earlier)
    content = "# Research Interests\n\n"
    content += f"*Updated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    content += "## My Research Focus\n\n"

    for interest in interests:
        content += f"- {interest}\n"

    content += "\n## Notes\n\n"
    content += "*These interests are used by the conference planner to match relevant "
    content += "talks and generate personalized schedules.*\n\n"
    content += "*To update: Run `python update_research_interests.py`*\n"

    with open(output_file, 'w') as f:
        f.write(content)

    print("\n" + "="*70)
    print("🎊 SUCCESS!")
    print("="*70)
    print(f"\n💾 Research interests saved to:")
    print(f"   {output_file}")
    print("\n💡 Next steps:")
    print("   - Use these interests with: python run_conference_planner.py")
    print("   - Or run: python phd_agent.py")
    print("   - Then type: conference plan ASHG2025")
    print("="*70 + "\n")


if __name__ == "__main__":
    update_research_interests()
