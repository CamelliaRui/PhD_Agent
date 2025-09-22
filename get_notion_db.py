#!/usr/bin/env python3
"""
Helper script to find Notion database IDs
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_databases():
    """List all accessible databases"""
    token = os.getenv('NOTION_TOKEN')
    
    if not token or token == 'your_notion_token_here':
        print("❌ Please set your NOTION_TOKEN in .env first")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28'
    }
    
    try:
        # Search for databases
        url = 'https://api.notion.com/v1/search'
        data = {
            "filter": {
                "value": "database",
                "property": "object"
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            results = response.json()
            databases = results.get('results', [])
            
            print(f"✅ Found {len(databases)} accessible databases:")
            for i, db in enumerate(databases, 1):
                print(f"{i}. {db.get('title', [{}])[0].get('text', {}).get('content', 'Untitled')}")
                print(f"   ID: {db['id']}")
                print(f"   URL: {db['url']}")
                print()
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔍 Finding your Notion databases...")
    list_databases()