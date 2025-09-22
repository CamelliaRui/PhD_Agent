#!/usr/bin/env python3
"""
Test script for PhD Agent functionality
"""

import asyncio
import sys
from phd_agent import PhdAgent


async def test_paper_search():
    """Test paper search functionality"""
    print("🧪 Testing paper search...")
    
    agent = PhdAgent()
    try:
        papers = await agent.search_papers("transformer attention mechanisms", max_results=3)
        
        if papers:
            print(f"✅ Found {len(papers)} papers")
            for i, paper in enumerate(papers, 1):
                print(f"  {i}. {paper.get('title', 'No title')}")
        else:
            print("⚠️ No papers found")
            
    except Exception as e:
        print(f"❌ Paper search failed: {e}")


async def test_brainstorming():
    """Test brainstorming functionality"""
    print("\n🧪 Testing brainstorming...")
    
    agent = PhdAgent()
    try:
        ideas = await agent.brainstorm_ideas("machine learning interpretability")
        
        if ideas:
            print("✅ Generated research ideas")
            print(ideas[:200] + "..." if len(ideas) > 200 else ideas)
        else:
            print("⚠️ No ideas generated")
            
    except Exception as e:
        print(f"❌ Brainstorming failed: {e}")


async def test_github_integration():
    """Test GitHub integration (if configured)"""
    print("\n🧪 Testing GitHub integration...")
    
    from mcp_integrations import GitHubMCPIntegration
    
    github = GitHubMCPIntegration()
    try:
        # Test with a public GitHub username (replace with actual username to test)
        activity = await github.get_weekly_activity("octocat")
        
        if 'error' not in activity:
            print("✅ GitHub integration working")
            print(f"  Commits: {len(activity.get('commits', []))}")
            print(f"  Issues: {len(activity.get('issues', []))}")
            print(f"  PRs: {len(activity.get('pull_requests', []))}")
        else:
            print(f"⚠️ GitHub integration: {activity.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ GitHub integration failed: {e}")


async def test_notion_integration():
    """Test Notion integration (if configured)"""
    print("\n🧪 Testing Notion integration...")
    
    from mcp_integrations import NotionMCPIntegration
    
    notion = NotionMCPIntegration()
    try:
        # Test creating a simple agenda
        agenda_items = [
            {
                "section": "Test Section",
                "content": "This is a test agenda item",
                "sub_items": ["Test sub-item 1", "Test sub-item 2"]
            }
        ]
        
        result = await notion.create_meeting_agenda("Test Meeting", agenda_items)
        
        if 'error' not in result:
            print("✅ Notion integration working")
            print(f"  Created page: {result.get('url', 'Success')}")
        else:
            print(f"⚠️ Notion integration: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Notion integration failed: {e}")


async def test_weekly_report():
    """Test weekly report generation"""
    print("\n🧪 Testing weekly report generation...")
    
    agent = PhdAgent()
    try:
        # Test without GitHub username first
        report = await agent.generate_weekly_report()
        
        if 'error' not in report:
            print("✅ Weekly report generation working")
            summary = report.get('summary', '')
            print(f"  Generated summary: {len(summary)} characters")
        else:
            print(f"⚠️ Weekly report: {report.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Weekly report failed: {e}")


def test_environment_setup():
    """Test environment setup"""
    print("🧪 Testing environment setup...")
    
    import os
    
    # Check for required API key
    if os.getenv('ANTHROPIC_API_KEY'):
        print("✅ ANTHROPIC_API_KEY found")
    else:
        print("⚠️ ANTHROPIC_API_KEY not found - required for full functionality")
    
    # Check for optional keys
    if os.getenv('GITHUB_TOKEN'):
        print("✅ GITHUB_TOKEN found")
    else:
        print("⚠️ GITHUB_TOKEN not found - GitHub integration will be limited")
    
    if os.getenv('NOTION_TOKEN'):
        print("✅ NOTION_TOKEN found")
    else:
        print("⚠️ NOTION_TOKEN not found - Notion integration disabled")
    
    # Test imports
    try:
        from claude_code_sdk import ClaudeSDKClient
        print("✅ Claude Code SDK imported successfully")
    except ImportError as e:
        print(f"❌ Claude Code SDK import failed: {e}")
    
    try:
        import requests
        print("✅ Requests library available")
    except ImportError:
        print("❌ Requests library not available")


async def main():
    """Run all tests"""
    print("🎓 PhD Agent Test Suite")
    print("=" * 50)
    
    # Test environment
    test_environment_setup()
    
    # Test core functionality
    await test_paper_search()
    await test_brainstorming()
    
    # Test integrations
    await test_github_integration()
    await test_notion_integration()
    
    # Test report generation
    await test_weekly_report()
    
    print("\n" + "=" * 50)
    print("🏁 Test suite completed!")
    print("\n💡 To run the full agent, use: python3 phd_agent.py")


if __name__ == "__main__":
    asyncio.run(main())