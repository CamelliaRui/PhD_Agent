#!/usr/bin/env python3
"""
PhD Agent - An AI assistant for PhD students using Claude Code SDK

Features:
1. Web search and academic paper retrieval
2. Paper summarization and discussion
3. Brainstorming and idea generation
4. GitHub activity tracking via MCP
5. Notion integration for meeting agendas via MCP
6. Weekly report generation
"""

import asyncio
import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from datetime import datetime

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from paper_search import PaperSearcher
from paper_analyzer import PaperAnalyzer
from mcp_integrations import GitHubMCPIntegration, NotionMCPIntegration
from slack_mcp_integration import SlackMCPIntegration
from zotero_mcp_integration import ZoteroMCPIntegration
from slack_paper_monitor import SlackPaperMonitor

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PhdAgent:
    """Main PhD Agent class that orchestrates all functionality"""
    
    def __init__(self):
        self.client = None
        self.paper_searcher = PaperSearcher()
        self.paper_analyzer = PaperAnalyzer()
        self.github_integration = GitHubMCPIntegration()
        self.notion_integration = NotionMCPIntegration()
        self.slack_integration = SlackMCPIntegration()
        self.zotero_integration = ZoteroMCPIntegration()
        self.paper_monitor = SlackPaperMonitor()
        self.setup_claude_client()
    
    def setup_claude_client(self):
        """Initialize Claude SDK client with appropriate options"""
        options = ClaudeCodeOptions(
            system_prompt="""You are a PhD Agent assistant specializing in:
            1. Academic research and paper analysis
            2. Web search for scholarly content
            3. Summarization and discussion of research papers
            4. Brainstorming research ideas
            5. GitHub activity tracking and analysis
            6. Notion integration for meeting preparation
            7. Slack conversation monitoring and research discussion extraction
            8. Weekly report generation for advisor meetings

            You have access to web search, file operations, and MCP integrations including Slack.
            Always provide scholarly, well-researched responses.""",
            allowed_tools=["WebSearch", "WebFetch", "Read", "Write", "Edit", "Bash"],
            max_turns=10,
            permission_mode="acceptEdits"
        )
        
        self.client = ClaudeSDKClient(options=options)
    
    async def search_papers(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for academic papers using integrated search"""
        try:
            papers = await self.paper_searcher.search_papers(query, max_results=max_results)
            return papers
        except Exception as e:
            logger.error(f"Error searching papers: {e}")
            return []
    
    async def summarize_paper(self, paper_content: str) -> str:
        """Summarize a research paper"""
        try:
            async with self.client as client:
                await client.query(f"""
                Please provide a comprehensive summary of this research paper:
                
                {paper_content}
                
                Include:
                1. Main research question and hypothesis
                2. Methodology used
                3. Key findings and results
                4. Implications and significance
                5. Limitations and future work
                6. How this relates to current research trends
                """)
                
                summary = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                summary += block.text
                
                return summary
        
        except Exception as e:
            logger.error(f"Error summarizing paper: {e}")
            return ""
    
    async def brainstorm_ideas(self, research_area: str, current_work: str = "") -> str:
        """Generate research ideas and suggestions"""
        try:
            async with self.client as client:
                prompt = f"""
                Based on the research area: "{research_area}"
                """
                
                if current_work:
                    prompt += f"And current work: {current_work}"
                
                prompt += """
                Please brainstorm:
                1. Novel research questions and hypotheses
                2. Potential methodological approaches
                3. Collaboration opportunities
                4. Grant funding possibilities
                5. Publication strategies
                6. Connections to other research areas
                """
                
                await client.query(prompt)
                
                ideas = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                ideas += block.text
                
                return ideas
        
        except Exception as e:
            logger.error(f"Error generating ideas: {e}")
            return ""
    
    async def generate_weekly_report(self, github_username: str = None) -> Dict[str, Any]:
        """Generate weekly activity report using GitHub MCP and create Notion agenda"""
        try:
            report_data = {
                'github_activity': {},
                'meeting_agenda': {},
                'summary': ''
            }
            
            # Get GitHub activity if username provided
            github_activity = {}
            if github_username:
                github_activity = await self.github_integration.get_weekly_activity(github_username)
                report_data['github_activity'] = github_activity
            
            # Generate summary using Claude
            async with self.client as client:
                activity_summary = ""
                if github_activity and 'error' not in github_activity:
                    activity_summary = f"""
                    GitHub Activity Summary:
                    - Commits: {len(github_activity.get('commits', []))}
                    - Issues: {len(github_activity.get('issues', []))}
                    - Pull Requests: {len(github_activity.get('pull_requests', []))}
                    - Active Repositories: {', '.join(github_activity.get('repositories', []))}
                    """
                
                await client.query(f"""
                Based on this weekly activity data:
                {activity_summary}
                
                Please generate:
                1. A comprehensive weekly progress report
                2. Key accomplishments and milestones
                3. Challenges encountered and how they were addressed
                4. Research insights and discoveries
                5. Questions to discuss with advisor
                6. Goals for next week
                7. Any decisions that need advisor input
                
                Format this as a structured report suitable for an advisor meeting.
                """)
                
                summary = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                summary += block.text
                
                report_data['summary'] = summary
            
            # Create Notion agenda
            agenda_items = self._parse_agenda_from_summary(summary)
            meeting_title = f"Weekly Advisor Meeting - {datetime.now().strftime('%Y-%m-%d')}"
            
            notion_result = await self.notion_integration.create_meeting_agenda(
                meeting_title, agenda_items
            )
            report_data['meeting_agenda'] = notion_result
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return {"error": str(e)}
    
    def _parse_agenda_from_summary(self, summary: str) -> List[Dict[str, Any]]:
        """Parse meeting agenda items from the generated summary"""
        # Simple parsing logic - could be enhanced with more sophisticated NLP
        agenda_items = [
            {
                "section": "Progress Updates",
                "content": "Research and development progress this week",
                "sub_items": []
            },
            {
                "section": "Technical Discussion",
                "content": "Questions and challenges for advisor input",
                "sub_items": []
            },
            {
                "section": "Next Steps", 
                "content": "Goals and plans for upcoming week",
                "sub_items": []
            }
        ]
        
        # Extract key points from summary to populate sub_items
        lines = summary.split('\n')
        current_section = 0
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:
                # Simple heuristic to categorize content
                if any(word in line.lower() for word in ['accomplished', 'completed', 'finished', 'done']):
                    agenda_items[0]['sub_items'].append(line[:100] + "..." if len(line) > 100 else line)
                elif any(word in line.lower() for word in ['question', 'challenge', 'issue', 'problem']):
                    agenda_items[1]['sub_items'].append(line[:100] + "..." if len(line) > 100 else line)
                elif any(word in line.lower() for word in ['next', 'future', 'plan', 'goal']):
                    agenda_items[2]['sub_items'].append(line[:100] + "..." if len(line) > 100 else line)
        
        return agenda_items

    async def monitor_slack_research(self, keywords: List[str] = None, days_back: int = 7) -> Dict[str, Any]:
        """Monitor Slack for research discussions and extract insights"""
        try:
            # Test Slack connection
            connection = await self.slack_integration.test_connection()
            if 'error' in connection:
                return {"error": f"Slack connection failed: {connection['error']}"}

            # Use default keywords if not provided
            if not keywords:
                keywords = ['research', 'paper', 'experiment', 'hypothesis', 'data', 'analysis', 'results']

            # Extract research discussions
            discussions = await self.slack_integration.extract_research_discussions(keywords, days_back)

            # Generate insights using Claude
            async with self.client as client:
                discussion_summary = f"""
                Research Discussions Found:
                - Papers mentioned: {len(discussions.get('papers', []))}
                - Research ideas: {len(discussions.get('ideas', []))}
                - Questions raised: {len(discussions.get('questions', []))}
                - Resources shared: {len(discussions.get('resources', []))}
                - Meetings discussed: {len(discussions.get('meetings', []))}
                """

                await client.query(f"""
                Based on these Slack research discussions from the past {days_back} days:
                {discussion_summary}

                Please provide:
                1. Key research themes and topics being discussed
                2. Important papers or resources mentioned
                3. Collaboration opportunities identified
                4. Urgent questions that need attention
                5. Action items and next steps
                6. Potential research directions emerging from discussions
                """)

                insights = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                insights += block.text

                return {
                    'discussions': discussions,
                    'insights': insights,
                    'workspace': connection.get('workspace', {})
                }

        except Exception as e:
            logger.error(f"Error monitoring Slack: {e}")
            return {"error": str(e)}

    async def get_slack_channel_summary(self, channel_name: str = None, hours_back: int = 24) -> Dict[str, Any]:
        """Get summary of specific Slack channel activity"""
        try:
            # List channels to find the target channel
            channels = await self.slack_integration.list_channels()

            if not channels:
                return {"error": "No channels found or accessible"}

            # Find target channel
            target_channel = None
            if channel_name:
                for channel in channels:
                    if channel['name'] == channel_name:
                        target_channel = channel
                        break
            else:
                # Use first channel if no specific channel provided
                target_channel = channels[0] if channels else None

            if not target_channel:
                return {"error": f"Channel '{channel_name}' not found"}

            # Get channel summary
            summary = await self.slack_integration.summarize_channel_activity(
                target_channel['id'],
                hours_back
            )

            # Get recent messages for context
            messages = await self.slack_integration.get_channel_messages(
                target_channel['id'],
                limit=50
            )

            return {
                'channel': target_channel,
                'summary': summary,
                'recent_messages': messages[:10],  # Return top 10 recent messages
                'total_messages': len(messages)
            }

        except Exception as e:
            logger.error(f"Error getting Slack channel summary: {e}")
            return {"error": str(e)}

    async def search_slack_messages(self, query: str, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search Slack messages for specific content"""
        try:
            results = await self.slack_integration.search_messages(
                query=query,
                channel=channel,
                count=50
            )

            return results

        except Exception as e:
            logger.error(f"Error searching Slack: {e}")
            return []

    async def interactive_session(self):
        """Start an interactive session with the PhD Agent"""
        print("🎓 PhD Agent initialized! How can I help you today?")
        print("Available commands:")
        print("1. 'search [query]' - Search for academic papers")
        print("2. 'analyze [paper_url_or_content]' - Analyze and summarize a paper")
        print("3. 'brainstorm [research_area]' - Generate research ideas")
        print("4. 'report [github_username]' - Generate weekly report and meeting agenda")
        print("5. 'slack monitor [keywords]' - Monitor Slack for research discussions")
        print("6. 'slack channel [channel_name]' - Get Slack channel summary")
        print("7. 'slack search [query]' - Search Slack messages")
        print("8. 'slack papers [hours]' - Check #paper channel (default: 168 hours/7 days)")
        print("9. 'chat [message]' - General discussion")
        print("10. 'quit' - Exit")
        
        while True:
            try:
                user_input = input("\n📝 You: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 Goodbye!")
                    break
                
                if user_input.startswith('search '):
                    query = user_input[7:]
                    print(f"🔍 Searching for papers on: {query}")
                    papers = await self.search_papers(query)
                    for i, paper in enumerate(papers, 1):
                        print(f"\n📄 Paper {i}: {paper.get('title', 'No title')}")
                        print(f"   Authors: {', '.join(paper.get('authors', []))}")
                        print(f"   Source: {paper.get('source', 'Unknown')}")
                        print(f"   Abstract: {paper.get('abstract', 'No abstract')[:200]}...")
                        if paper.get('url'):
                            print(f"   URL: {paper['url']}")
                
                elif user_input.startswith('analyze '):
                    url_or_content = user_input[8:]
                    print(f"📊 Analyzing paper...")
                    if url_or_content.startswith('http'):
                        analysis = await self.paper_analyzer.analyze_paper_from_url(url_or_content)
                    else:
                        analysis = await self.paper_analyzer.analyze_paper_text(url_or_content)
                    print(f"\n📋 Analysis:\n{analysis.get('analysis', analysis)}")
                
                elif user_input.startswith('brainstorm '):
                    area = user_input[11:]
                    print(f"💡 Brainstorming ideas for: {area}")
                    ideas = await self.brainstorm_ideas(area)
                    print(f"\n🧠 Ideas:\n{ideas}")
                
                elif user_input.startswith('report'):
                    parts = user_input.split(' ', 1)
                    github_username = parts[1] if len(parts) > 1 else None
                    print("📊 Generating weekly report and meeting agenda...")
                    report = await self.generate_weekly_report(github_username)

                    if 'error' in report:
                        print(f"❌ Error: {report['error']}")
                    else:
                        print(f"\n📈 Weekly Report:\n{report.get('summary', 'No summary generated')}")
                        if report.get('meeting_agenda'):
                            print(f"\n📝 Notion agenda created: {report['meeting_agenda'].get('url', 'Success')}")

                elif user_input.startswith('slack monitor'):
                    parts = user_input.split(' ', 2)
                    keywords = parts[2].split(',') if len(parts) > 2 else None
                    print("💬 Monitoring Slack for research discussions...")
                    results = await self.monitor_slack_research(keywords)

                    if 'error' in results:
                        print(f"❌ Error: {results['error']}")
                    else:
                        discussions = results.get('discussions', {})
                        print(f"\n📊 Slack Research Activity:")
                        print(f"  Papers discussed: {len(discussions.get('papers', []))}")
                        print(f"  Ideas shared: {len(discussions.get('ideas', []))}")
                        print(f"  Questions raised: {len(discussions.get('questions', []))}")
                        print(f"  Resources shared: {len(discussions.get('resources', []))}")
                        print(f"\n💡 Insights:\n{results.get('insights', 'No insights generated')}")

                elif user_input.startswith('slack channel'):
                    parts = user_input.split(' ', 2)
                    channel_name = parts[2] if len(parts) > 2 else None
                    print(f"📡 Getting summary for channel: {channel_name or 'default'}")
                    summary = await self.get_slack_channel_summary(channel_name)

                    if 'error' in summary:
                        print(f"❌ Error: {summary['error']}")
                    else:
                        channel_info = summary.get('channel', {})
                        activity = summary.get('summary', {})
                        print(f"\n📊 Channel: #{channel_info.get('name', 'unknown')}")
                        print(f"  Members: {channel_info.get('num_members', 0)}")
                        print(f"  Messages (24h): {activity.get('total_messages', 0)}")
                        print(f"  Active users: {activity.get('unique_users', 0)}")
                        print(f"  Threads: {activity.get('thread_count', 0)}")
                        print(f"  Top contributors:")
                        for contributor in activity.get('top_contributors', [])[:3]:
                            print(f"    - {contributor['user']}: {contributor['messages']} messages")

                elif user_input.startswith('slack search'):
                    query = user_input[12:].strip()
                    if query:
                        print(f"🔍 Searching Slack for: {query}")
                        messages = await self.search_slack_messages(query)

                        if messages:
                            print(f"\n📨 Found {len(messages)} messages:")
                            for i, msg in enumerate(messages[:5], 1):
                                print(f"\n{i}. {msg.get('user', 'Unknown')}")
                                print(f"   Channel: #{msg.get('channel', 'unknown')}")
                                print(f"   Message: {msg.get('text', '')[:200]}...")
                                if msg.get('permalink'):
                                    print(f"   Link: {msg['permalink']}")
                        else:
                            print("No messages found.")
                    else:
                        print("❓ Please provide a search query.")

                elif user_input.startswith('slack papers'):
                    parts = user_input.split()
                    hours = 168  # Default to 7 days
                    if len(parts) > 2:
                        try:
                            hours = int(parts[2])
                        except:
                            hours = 168
                    print(f"📚 Checking #paper channel for papers from the last {hours} hours...")
                    await self.paper_monitor.run_once(hours_back=hours)

                elif user_input.startswith('chat '):
                    message = user_input[5:]
                    async with self.client as client:
                        await client.query(message)
                        async for response in client.receive_response():
                            if hasattr(response, 'content'):
                                for block in response.content:
                                    if hasattr(block, 'text'):
                                        print(f"\n🤖 PhD Agent: {block.text}")
                
                else:
                    print("❓ Unknown command. Type 'quit' to exit or use one of the available commands.")
            
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                print(f"❌ Error: {e}")


async def main():
    """Main entry point"""
    agent = PhdAgent()
    await agent.interactive_session()


if __name__ == "__main__":
    asyncio.run(main())