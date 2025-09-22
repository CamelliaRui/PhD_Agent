#!/usr/bin/env python3
"""
Simple meeting agenda generator that creates the Notion template
Requires manual input of progress items or can be integrated with git log
"""

from datetime import datetime
import argparse
import subprocess
import os


def get_local_git_commits(days: int = 7) -> list:
    """
    Get commits from local git repository
    """
    commits = []
    try:
        # Check if we're in a git repository
        subprocess.run(['git', 'rev-parse', '--git-dir'],
                      capture_output=True, check=True)

        # Get commits from the last N days
        cmd = [
            'git', 'log',
            f'--since={days}.days.ago',
            '--pretty=format:%h|%ad|%s',
            '--date=short',
            '--author=Camellia'  # Filter by author name
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line:
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        commits.append({
                            'sha': parts[0],
                            'date': parts[1],
                            'message': parts[2]
                        })
    except subprocess.CalledProcessError:
        print("Note: Not in a git repository or git not available")

    return commits


def generate_meeting_agenda_template(progress_items: list = None) -> str:
    """
    Generate meeting agenda in Notion template format
    """
    agenda = "## Progress over the week:\n\n"

    if progress_items:
        for i, item in enumerate(progress_items[:3], 1):
            agenda += f"{i}. {item}\n\n"
        for i in range(len(progress_items) + 1, 4):
            agenda += f"{i}.\n\n"
    else:
        agenda += "1.\n\n2.\n\n3.\n\n"

    agenda += "## Results & Obstacles\n\n"
    agenda += "1.\n\n2.\n\n3.\n\n"

    agenda += "## Plan for Next Week\n\n"
    agenda += "1.\n\n2.\n\n3."

    return agenda


def main():
    parser = argparse.ArgumentParser(description='Generate meeting agenda template')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='Number of days to look back for git commits (default: 7)')
    parser.add_argument('--output', '-o', help='Output file path (optional)')
    parser.add_argument('--use-git', action='store_true',
                        help='Try to get commits from local git repo')

    args = parser.parse_args()

    progress_items = []

    if args.use_git:
        commits = get_local_git_commits(args.days)
        if commits:
            print(f"Found {len(commits)} commits from the last {args.days} days")
            # Format commits as progress items
            for commit in commits[:3]:  # Take top 3
                progress_items.append(f"{commit['message']} ({commit['sha']})")

    agenda = generate_meeting_agenda_template(progress_items)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(agenda)
        print(f"Meeting agenda saved to {args.output}")
    else:
        print("\n" + "="*50)
        print("MEETING AGENDA TEMPLATE")
        print("="*50 + "\n")
        print(agenda)
        print("\n" + "="*50)
        print("Fill in the template with your weekly progress!")


if __name__ == '__main__':
    main()