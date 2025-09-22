#!/usr/bin/env python3
"""
Simple Notion API test to debug database structure
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_notion_database():
    """Test Notion database access and structure"""
    token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not token or not database_id:
        print("❌ Missing Notion token or database ID")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    # First, get database schema
    print("🔍 Checking database structure...")
    db_url = f'https://api.notion.com/v1/databases/{database_id}'
    
    try:
        response = requests.get(db_url, headers=headers)
        
        if response.status_code == 200:
            db_data = response.json()
            print("✅ Database accessible")
            print(f"Title: {db_data.get('title', [{}])[0].get('text', {}).get('content', 'No title')}")
            
            print("\nProperties:")
            for prop_name, prop_data in db_data.get('properties', {}).items():
                print(f"  - {prop_name}: {prop_data.get('type')}")
            
            # Try to create a simple page
            print("\n🧪 Testing page creation...")
            page_data = {
                "parent": {"database_id": database_id},
                "properties": {
                    "Name": {  # Using "Name" as it's common default
                        "title": [
                            {
                                "text": {
                                    "content": "Test Meeting Agenda"
                                }
                            }
                        ]
                    }
                }
            }
            
            page_url = 'https://api.notion.com/v1/pages'
            page_response = requests.post(page_url, headers=headers, json=page_data)
            
            if page_response.status_code == 200:
                print("✅ Page creation successful!")
                result = page_response.json()
                print(f"Created page: {result.get('url')}")
            else:
                print(f"❌ Page creation failed: {page_response.status_code}")
                print(f"Response: {page_response.text}")
                
                # Suggest creating a compatible database
                print("\n💡 Try creating a new database with these properties:")
                print("  - Name (Title)")
                print("  - Date (Date)")
                print("  - Type (Select)")
        
        else:
            print(f"❌ Database access failed: {response.status_code}")
            print(f"Response: {response.text}")
            print("\n💡 Make sure to:")
            print("  1. Share your database with the integration")
            print("  2. Use the correct database ID from the URL")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_notion_database()