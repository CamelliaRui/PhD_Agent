"""
Slack Paper Monitor - Monitors #paper channel and offers to save papers to Zotero
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

from slack_mcp_integration import SlackMCPIntegration
from zotero_mcp_integration import ZoteroMCPIntegration

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackPaperMonitor:
    """Monitor Slack #paper channel for papers and save to Zotero"""

    def __init__(self):
        self.slack = SlackMCPIntegration()
        self.zotero = ZoteroMCPIntegration()
        self.processed_messages = set()  # Track processed message timestamps

    async def find_paper_channel(self) -> Optional[str]:
        """Find the #paper channel ID"""
        try:
            channels = await self.slack.list_channels()
            for channel in channels:
                if channel['name'] == 'paper' or channel['name'] == 'papers':
                    return channel['id']
            return None
        except Exception as e:
            logger.error(f"Error finding paper channel: {e}")
            return None

    async def get_recent_papers(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent papers posted in #paper channel

        Args:
            hours_back: How many hours to look back

        Returns:
            List of detected papers with metadata
        """
        # Find paper channel
        paper_channel_id = await self.find_paper_channel()
        if not paper_channel_id:
            logger.error("Could not find #paper channel")
            return []

        # Get recent messages
        start_time = datetime.now() - timedelta(hours=hours_back)
        messages = await self.slack.get_channel_messages(
            paper_channel_id,
            start_time=start_time,
            limit=100
        )

        detected_papers = []

        for msg in messages:
            # Skip if already processed
            msg_ts = msg.get('ts')
            if msg_ts in self.processed_messages:
                continue

            # Extract paper references from message
            text = msg.get('text', '')
            papers = self.zotero.extract_paper_references(text)

            for paper in papers:
                # Fetch metadata
                metadata = await self.zotero.fetch_paper_metadata(paper)

                # Check if already in Zotero
                exists = False
                if metadata.get('doi'):
                    exists = await self.zotero.check_if_exists(metadata['doi'], 'doi')
                elif metadata.get('url'):
                    exists = await self.zotero.check_if_exists(metadata['url'], 'url')

                paper_info = {
                    'message': {
                        'user': msg.get('user'),
                        'timestamp': msg.get('timestamp'),
                        'text': text[:200] + '...' if len(text) > 200 else text
                    },
                    'paper': paper,
                    'metadata': metadata,
                    'already_in_zotero': exists
                }

                detected_papers.append(paper_info)

            # Mark message as processed
            self.processed_messages.add(msg_ts)

        return detected_papers

    async def interactive_paper_review(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Interactive review of detected papers

        Args:
            papers: List of detected papers

        Returns:
            List of papers user wants to save
        """
        if not papers:
            print("No new papers found in #paper channel.")
            return []

        papers_to_save = []

        print(f"\n📚 Found {len(papers)} paper(s) in #paper channel:\n")

        for i, paper_info in enumerate(papers, 1):
            metadata = paper_info['metadata']
            msg = paper_info['message']

            print(f"\n{'='*60}")
            print(f"Paper {i}/{len(papers)}")
            print(f"{'='*60}")

            print(f"\n📄 Title: {metadata.get('title', 'Unknown')}")
            print(f"👥 Authors: {', '.join(metadata.get('authors', ['Unknown'])[:3])}")
            if len(metadata.get('authors', [])) > 3:
                print(f"   ... and {len(metadata['authors']) - 3} more")

            print(f"📅 Year: {metadata.get('year', 'Unknown')}")
            print(f"📖 Journal: {metadata.get('journal', 'Unknown')}")

            if metadata.get('doi'):
                print(f"🔗 DOI: {metadata['doi']}")

            print(f"\n🔗 URL: {metadata.get('url', 'N/A')}")
            print(f"📝 Type: {paper_info['paper']['type'].upper()}")

            print(f"\n💬 Posted by: {msg['user']}")
            print(f"🕐 Posted at: {msg['timestamp']}")
            print(f"📨 Message: {msg['text']}")

            if paper_info['already_in_zotero']:
                print("\n⚠️  This paper is already in your Zotero library!")
                continue

            # Ask user if they want to save this paper
            while True:
                response = input("\n💾 Save to Zotero? (y/n/s for skip all): ").strip().lower()

                if response == 'y':
                    # Optional: Ask for collection
                    collections = await self.zotero.get_collections()
                    if collections:
                        print("\n📁 Available collections:")
                        for j, col in enumerate(collections[:10], 1):
                            print(f"  {j}. {col['name']}")
                        print("  0. No collection (add to library root)")

                        col_choice = input("\nSelect collection (0-10): ").strip()
                        try:
                            col_idx = int(col_choice)
                            if 0 < col_idx <= len(collections):
                                paper_info['collection_id'] = collections[col_idx - 1]['key']
                        except:
                            pass

                    papers_to_save.append(paper_info)
                    print("✅ Marked for saving to Zotero")
                    break

                elif response == 'n':
                    print("⏭️  Skipped")
                    break

                elif response == 's':
                    print("⏭️  Skipping all remaining papers")
                    return papers_to_save

                else:
                    print("Please enter 'y' for yes, 'n' for no, or 's' to skip all")

        return papers_to_save

    async def save_papers_to_zotero(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Save selected papers to Zotero

        Args:
            papers: List of papers to save

        Returns:
            Results of the save operations
        """
        results = []

        for paper_info in papers:
            metadata = paper_info['metadata']
            collection_id = paper_info.get('collection_id')

            print(f"\n💾 Saving: {metadata.get('title', 'Unknown')}...")

            result = await self.zotero.add_to_zotero(metadata, collection_id)

            if result.get('success'):
                print(f"✅ Successfully saved to Zotero!")
                results.append({
                    'success': True,
                    'title': metadata.get('title'),
                    'key': result.get('key')
                })
            else:
                print(f"❌ Failed to save: {result.get('error', 'Unknown error')}")
                results.append({
                    'success': False,
                    'title': metadata.get('title'),
                    'error': result.get('error')
                })

        return results

    async def monitor_continuously(self, check_interval_minutes: int = 30):
        """
        Continuously monitor #paper channel

        Args:
            check_interval_minutes: How often to check for new papers
        """
        print("🔄 Starting continuous monitoring of #paper channel...")
        print(f"Will check every {check_interval_minutes} minutes")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                # Get recent papers
                papers = await self.get_recent_papers(hours_back=1)

                if papers:
                    print(f"\n🔔 Found {len(papers)} new paper(s)!")

                    # Review and save
                    to_save = await self.interactive_paper_review(papers)

                    if to_save:
                        await self.save_papers_to_zotero(to_save)

                # Wait for next check
                print(f"\n⏰ Next check in {check_interval_minutes} minutes...")
                await asyncio.sleep(check_interval_minutes * 60)

            except KeyboardInterrupt:
                print("\n👋 Stopping monitor...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def run_once(self, hours_back: int = 24):
        """
        Run the monitor once for recent papers

        Args:
            hours_back: How many hours to look back
        """
        # Test connections
        slack_conn = await self.slack.test_connection()
        if 'error' in slack_conn:
            print(f"❌ Slack connection failed: {slack_conn['error']}")
            return

        zotero_conn = await self.zotero.test_connection()
        if 'error' in zotero_conn:
            print(f"❌ Zotero connection failed: {zotero_conn['error']}")
            print("\n📝 To set up Zotero:")
            print("1. Get your API key from: https://www.zotero.org/settings/keys")
            print("2. Get your user ID from: https://www.zotero.org/settings/keys")
            print("3. Add to .env:")
            print("   ZOTERO_API_KEY=your-api-key")
            print("   ZOTERO_LIBRARY_ID=your-user-id")
            print("   ZOTERO_LIBRARY_TYPE=user")
            return

        print(f"✅ Connected to Slack workspace: {slack_conn['workspace']['team']}")
        print(f"✅ Connected to Zotero library: {zotero_conn['library_id']}")

        # Find paper channel
        paper_channel_id = await self.find_paper_channel()
        if not paper_channel_id:
            print("❌ Could not find #paper channel in your Slack workspace")
            print("Make sure the bot has access to the #paper channel")
            return

        print(f"\n🔍 Checking #paper channel for papers from the last {hours_back} hours...")

        # Get recent papers
        papers = await self.get_recent_papers(hours_back=hours_back)

        if not papers:
            print("No new papers found in #paper channel.")
            return

        # Interactive review
        to_save = await self.interactive_paper_review(papers)

        # Save selected papers
        if to_save:
            print(f"\n📚 Saving {len(to_save)} paper(s) to Zotero...")
            results = await self.save_papers_to_zotero(to_save)

            # Summary
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful

            print(f"\n📊 Summary:")
            print(f"  ✅ Successfully saved: {successful}")
            if failed > 0:
                print(f"  ❌ Failed: {failed}")
        else:
            print("\nNo papers selected for saving.")


async def main():
    """Main entry point for the paper monitor"""
    monitor = SlackPaperMonitor()

    print("📚 Slack Paper Monitor for Zotero")
    print("================================\n")

    print("Select mode:")
    print("1. Check recent papers (one-time)")
    print("2. Monitor continuously")
    print("3. Check specific time period")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        await monitor.run_once(hours_back=24)

    elif choice == '2':
        interval = input("Check interval in minutes (default 30): ").strip()
        try:
            interval = int(interval)
        except:
            interval = 30
        await monitor.monitor_continuously(check_interval_minutes=interval)

    elif choice == '3':
        hours = input("How many hours to look back: ").strip()
        try:
            hours = int(hours)
        except:
            hours = 24
        await monitor.run_once(hours_back=hours)

    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())