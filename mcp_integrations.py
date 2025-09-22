"""
MCP integrations for GitHub and Notion
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
import json


class GitHubMCPIntegration:
    """GitHub MCP integration for tracking research activity"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        } if self.token else {}
        self.base_url = 'https://api.github.com'
    
    async def get_weekly_activity(self, username: str, days: int = 7) -> Dict[str, Any]:
        """Get GitHub activity for the past week"""
        if not self.token:
            return {"error": "GitHub token not configured"}
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            activity_data = {
                'commits': await self._get_commits(username, start_date, end_date),
                'issues': await self._get_issues(username, start_date, end_date),
                'pull_requests': await self._get_pull_requests(username, start_date, end_date),
                'repositories': await self._get_active_repositories(username, start_date, end_date)
            }
            
            return activity_data
            
        except Exception as e:
            return {"error": f"Error fetching GitHub activity: {str(e)}"}
    
    async def _get_commits(self, username: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get commits made by user in date range, filtered to mancusolab organization"""
        try:
            # Search for commits by user in mancusolab organization only
            query = f"author:{username} org:mancusolab author-date:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
            url = f"{self.base_url}/search/commits?q={query}&sort=author-date&order=desc"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            commits = []

            for item in data.get('items', []):
                # Double-check that the repository belongs to mancusolab
                repo_full_name = item['repository']['full_name']
                if repo_full_name.startswith('mancusolab/'):
                    commit = {
                        'sha': item['sha'][:8],
                        'message': item['commit']['message'],
                        'date': item['commit']['author']['date'],
                        'repository': repo_full_name,
                        'url': item['html_url']
                    }
                    commits.append(commit)

            return commits

        except Exception as e:
            print(f"Error fetching commits: {e}")
            return []
    
    async def _get_issues(self, username: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get issues created or updated by user in mancusolab organization"""
        try:
            # Search for issues involving user in mancusolab organization only
            query = f"involves:{username} org:mancusolab updated:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
            url = f"{self.base_url}/search/issues?q={query}&sort=updated&order=desc"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            issues = []
            
            for item in data.get('items', []):
                issue = {
                    'number': item['number'],
                    'title': item['title'],
                    'state': item['state'],
                    'updated_at': item['updated_at'],
                    'repository': item['repository_url'].split('/')[-1],
                    'url': item['html_url']
                }
                issues.append(issue)
            
            return issues
            
        except Exception as e:
            print(f"Error fetching issues: {e}")
            return []
    
    async def _get_pull_requests(self, username: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get pull requests created by user in mancusolab organization"""
        try:
            query = f"author:{username} org:mancusolab created:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
            url = f"{self.base_url}/search/issues?q={query}+type:pr&sort=created&order=desc"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            prs = []
            
            for item in data.get('items', []):
                pr = {
                    'number': item['number'],
                    'title': item['title'],
                    'state': item['state'],
                    'created_at': item['created_at'],
                    'repository': item['repository_url'].split('/')[-1],
                    'url': item['html_url']
                }
                prs.append(pr)
            
            return prs
            
        except Exception as e:
            print(f"Error fetching pull requests: {e}")
            return []
    
    async def _get_active_repositories(self, username: str, start_date: datetime, end_date: datetime) -> List[str]:
        """Get repositories user was active in, filtered to mancusolab organization"""
        try:
            url = f"{self.base_url}/users/{username}/events?per_page=100"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            events = response.json()
            active_repos = set()

            for event in events:
                event_date = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
                if start_date <= event_date.replace(tzinfo=None) <= end_date:
                    repo_name = event['repo']['name']
                    # Only include repositories from mancusolab organization
                    if repo_name.startswith('mancusolab/'):
                        active_repos.add(repo_name)

            return list(active_repos)

        except Exception as e:
            print(f"Error fetching active repositories: {e}")
            return []

    async def get_repo_commits(self, username: str, repo_owner: str, repo_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get commits from a specific repository by a specific user across all branches"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # First, get all branches
            branches_url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/branches"
            branches_response = requests.get(branches_url, headers=self.headers, timeout=10)

            all_commits = []
            seen_shas = set()  # To avoid duplicates

            if branches_response.status_code == 200:
                branches = branches_response.json()
                print(f"Found {len(branches)} branches in {repo_owner}/{repo_name}")

                # Check commits in each branch
                for branch in branches:
                    branch_name = branch['name']
                    print(f"Checking branch: {branch_name}")

                    # Get commits from this specific branch
                    url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits"
                    params = {
                        'author': username,
                        'since': start_date.isoformat(),
                        'until': end_date.isoformat(),
                        'sha': branch_name,  # Specify the branch
                        'per_page': 100
                    }

                    response = requests.get(url, headers=self.headers, params=params, timeout=10)

                    if response.status_code == 200:
                        commits_data = response.json()

                        for commit in commits_data:
                            # Skip if we've already seen this commit
                            if commit['sha'] in seen_shas:
                                continue
                            seen_shas.add(commit['sha'])

                            # Verify the commit author matches the username
                            commit_author = commit.get('author', {}).get('login', '') if commit.get('author') else ''
                            commit_committer = commit.get('committer', {}).get('login', '') if commit.get('committer') else ''

                            if commit_author == username or commit_committer == username:
                                commit_info = {
                                    'sha': commit['sha'][:8],
                                    'message': commit['commit']['message'],
                                    'date': commit['commit']['author']['date'],
                                    'repository': f"{repo_owner}/{repo_name}",
                                    'branch': branch_name,
                                    'url': commit['html_url'],
                                    'author_name': commit['commit']['author']['name'],
                                    'author_email': commit['commit']['author']['email']
                                }
                                all_commits.append(commit_info)

            # Sort commits by date (newest first)
            all_commits.sort(key=lambda x: x['date'], reverse=True)
            return all_commits

        except Exception as e:
            print(f"Error fetching repository commits: {e}")
            return []

    async def get_scfm_analysis_activity(self, username: str, days: int = 7) -> Dict[str, Any]:
        """Get activity specifically from mancusolab/scfm_analysis repository"""
        try:
            # Get commits from scfm_analysis repo
            commits = await self.get_repo_commits(username, 'mancusolab', 'scfm_analysis', days)

            # Get issues from the repo
            issues = []
            try:
                url = f"{self.base_url}/repos/mancusolab/scfm_analysis/issues"
                params = {
                    'state': 'all',
                    'creator': username,
                    'per_page': 50
                }

                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                if response.status_code == 200:
                    issues_data = response.json()

                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)

                    for issue in issues_data:
                        updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                        if start_date <= updated_at.replace(tzinfo=None) <= end_date:
                            issue_info = {
                                'number': issue['number'],
                                'title': issue['title'],
                                'state': issue['state'],
                                'updated_at': issue['updated_at'],
                                'repository': 'mancusolab/scfm_analysis',
                                'url': issue['html_url']
                            }
                            issues.append(issue_info)

            except Exception as e:
                print(f"Error fetching issues: {e}")

            # Get pull requests from the repo
            pull_requests = []
            try:
                url = f"{self.base_url}/repos/mancusolab/scfm_analysis/pulls"
                params = {
                    'state': 'all',
                    'creator': username,
                    'per_page': 50
                }

                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                if response.status_code == 200:
                    prs_data = response.json()

                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)

                    for pr in prs_data:
                        created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                        if start_date <= created_at.replace(tzinfo=None) <= end_date:
                            pr_info = {
                                'number': pr['number'],
                                'title': pr['title'],
                                'state': pr['state'],
                                'created_at': pr['created_at'],
                                'repository': 'mancusolab/scfm_analysis',
                                'url': pr['html_url']
                            }
                            pull_requests.append(pr_info)

            except Exception as e:
                print(f"Error fetching pull requests: {e}")

            return {
                'commits': commits,
                'issues': issues,
                'pull_requests': pull_requests,
                'repositories': ['mancusolab/scfm_analysis'] if commits or issues or pull_requests else []
            }

        except Exception as e:
            return {"error": f"Error fetching scfm_analysis activity: {str(e)}"}


class NotionMCPIntegration:
    """Notion MCP integration for meeting agenda creation"""
    
    def __init__(self, token: Optional[str] = None, database_id: Optional[str] = None):
        self.token = token or os.getenv('NOTION_TOKEN')
        self.database_id = database_id or os.getenv('NOTION_DATABASE_ID')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        } if self.token else {}
        self.base_url = 'https://api.notion.com/v1'
    
    async def create_meeting_agenda(self, title: str, agenda_items: List[Dict[str, Any]], 
                                  meeting_date: Optional[str] = None) -> Dict[str, Any]:
        """Create a meeting agenda page in Notion"""
        if not self.token or not self.database_id:
            return {"error": "Notion token or database ID not configured"}
        
        try:
            # Create new page in database
            page_data = {
                "parent": {"database_id": self.database_id},
                "properties": {
                    "Title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    },
                    "Date": {
                        "date": {
                            "start": meeting_date or datetime.now().strftime('%Y-%m-%d')
                        }
                    } if meeting_date else {},
                    "Type": {
                        "select": {
                            "name": "Meeting Agenda"
                        }
                    }
                },
                "children": self._build_agenda_blocks(agenda_items)
            }
            
            url = f"{self.base_url}/pages"
            response = requests.post(url, headers=self.headers, json=page_data, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            return {"error": f"Error creating Notion page: {str(e)}"}
    
    def _build_agenda_blocks(self, agenda_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build Notion blocks for agenda items"""
        blocks = []
        
        # Add header
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": "Meeting Agenda"}}]
            }
        })
        
        # Add agenda items
        for item in agenda_items:
            # Section header
            if item.get('section'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": item['section']}}]
                    }
                })
            
            # Item content
            if item.get('content'):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": item['content']}}]
                    }
                })
            
            # Sub-items
            for sub_item in item.get('sub_items', []):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"  • {sub_item}"}}]
                    }
                })
        
        return blocks
    
    async def get_recent_pages(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recently created/updated pages from the database"""
        if not self.token or not self.database_id:
            return []
        
        try:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query_data = {
                "filter": {
                    "property": "Last edited time",
                    "last_edited_time": {
                        "after": start_date
                    }
                },
                "sorts": [
                    {
                        "property": "Last edited time",
                        "direction": "descending"
                    }
                ]
            }
            
            url = f"{self.base_url}/databases/{self.database_id}/query"
            response = requests.post(url, headers=self.headers, json=query_data, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except Exception as e:
            print(f"Error fetching recent pages: {e}")
            return []


# Example usage
async def main():
    # Test GitHub integration
    github = GitHubMCPIntegration()
    activity = await github.get_weekly_activity("your_username")
    print("GitHub Activity:", json.dumps(activity, indent=2))
    
    # Test Notion integration
    notion = NotionMCPIntegration()
    agenda_items = [
        {
            "section": "Progress Updates",
            "content": "Research progress this week",
            "sub_items": ["Completed literature review", "Started experiment design"]
        },
        {
            "section": "Questions for Advisor",
            "content": "Technical challenges and guidance needed",
            "sub_items": ["Methodology validation", "Timeline review"]
        }
    ]
    
    result = await notion.create_meeting_agenda("Weekly Advisor Meeting", agenda_items)
    print("Notion Agenda:", json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())