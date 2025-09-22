#!/usr/bin/env python3
"""
Generate meeting agenda from GitHub commits for CamelliaRui
Following the Notion template format
"""

import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict
import argparse


def get_github_commits(username: str, days: int = 7) -> List[Dict]:
    """
    Fetch GitHub commits for a user from the past N days
    """
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    query = f'''query {{
        user(login: "{username}") {{
            contributionsCollection(from: "{since_date}T00:00:00Z") {{
                commitContributionsByRepository {{
                    repository {{
                        name
                        owner {{
                            login
                        }}
                    }}
                    contributions(first: 100) {{
                        nodes {{
                            commitCount
                            occurredAt
                        }}
                    }}
                }}
            }}
        }}
    }}'''

    cmd = [
        'gh', 'api', 'graphql',
        '-f', f'query={query}'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching GitHub data: {e}")
        print(f"stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing GitHub response: {e}")
        return None


def get_recent_commits_details(username: str, days: int = 7) -> List[Dict]:
    """
    Get detailed commit information using gh cli
    """
    commits = []
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Get user's recent repos with activity
    cmd = [
        'gh', 'api', f'/users/{username}/events/public',
        '--paginate', '--jq',
        '.[] | select(.type == "PushEvent") | {repo: .repo.name, commits: .payload.commits, created: .created_at}'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line:
                    try:
                        event = json.loads(line)
                        repo_name = event.get('repo', '')
                        for commit in event.get('commits', []):
                            commits.append({
                                'repo': repo_name,
                                'message': commit.get('message', ''),
                                'sha': commit.get('sha', '')[:7],
                                'date': event.get('created', '')
                            })
                    except json.JSONDecodeError:
                        continue
    except subprocess.CalledProcessError as e:
        print(f"Error fetching commit details: {e}")

    return commits


def format_commits_for_progress(commits: List[Dict]) -> List[str]:
    """
    Format commits into progress items
    """
    progress_items = []
    repo_commits = {}

    # Group commits by repository
    for commit in commits:
        repo = commit.get('repo', 'Unknown')
        if repo not in repo_commits:
            repo_commits[repo] = []
        repo_commits[repo].append(commit['message'].split('\n')[0])  # First line only

    # Format as progress items
    for repo, messages in repo_commits.items():
        if len(messages) == 1:
            progress_items.append(f"Updated {repo}: {messages[0]}")
        else:
            progress_items.append(f"Multiple updates to {repo} ({len(messages)} commits)")
            for msg in messages[:3]:  # Show first 3 commit messages
                progress_items.append(f"  - {msg}")

    return progress_items[:3]  # Return top 3 items for the template


def generate_meeting_agenda(username: str, days: int = 7) -> str:
    """
    Generate the meeting agenda in Notion template format
    """
    # Get commits
    commits = get_recent_commits_details(username, days)

    # Format progress items
    progress_items = format_commits_for_progress(commits)

    # Fill in template
    agenda = f"## Progress over the week:\n\n"

    if progress_items:
        for i, item in enumerate(progress_items, 1):
            agenda += f"{i}. {item}\n\n"
        for i in range(len(progress_items) + 1, 4):
            agenda += f"{i}.\n\n"
    else:
        agenda += "1.\n\n2.\n\n3.\n\n"

    agenda += "## Results & Obstacles\n\n1.\n\n2.\n\n3.\n\n"
    agenda += "## Plan for Next Week\n\n1.\n\n2.\n\n3."

    return agenda


def main():
    parser = argparse.ArgumentParser(description='Generate meeting agenda from GitHub commits')
    parser.add_argument('--username', '-u', default='CamelliaRui',
                        help='GitHub username (default: CamelliaRui)')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='Number of days to look back (default: 7)')
    parser.add_argument('--output', '-o', help='Output file path (optional)')

    args = parser.parse_args()

    print(f"Fetching GitHub commits for {args.username} from the past {args.days} days...")

    agenda = generate_meeting_agenda(args.username, args.days)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(agenda)
        print(f"Meeting agenda saved to {args.output}")
    else:
        print("\n" + "="*50)
        print("MEETING AGENDA")
        print("="*50 + "\n")
        print(agenda)


if __name__ == '__main__':
    main()