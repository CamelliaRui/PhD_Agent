# Slack-Zotero Integration Setup Guide

## Overview
This integration monitors your Slack #paper (or #papers) channel for research papers and offers to save them directly to your Zotero library.

## Features
- Automatic detection of papers from:
  - arXiv links
  - DOI references
  - PubMed articles
  - bioRxiv/medRxiv preprints
  - Nature, Science, Cell, PLOS, IEEE, ACM papers
  - Direct PDF links
- Fetches paper metadata automatically
- Interactive review before saving
- Duplicate detection (won't add papers already in Zotero)
- Choose Zotero collections for organization

## Setup Instructions

### 1. Add Bot to #papers Channel

**In Slack:**
1. Go to the #papers channel
2. Click the channel name at the top
3. Select "Integrations" or "Settings"
4. Click "Add an app"
5. Search for your bot "camellias_agent"
6. Click "Add to channel"

**Alternative method:**
- In the #papers channel, type: `/invite @camellias_agent`

### 2. Configure Zotero

1. **Get Zotero API Key:**
   - Go to https://www.zotero.org/settings/keys
   - Click "Create new private key"
   - Give it a name like "PhD Agent Integration"
   - Check these permissions:
     - ✅ Library - Allow library access
     - ✅ Notes - Allow notes access
     - ✅ Write - Allow write access
   - Click "Save Key"
   - Copy the generated key

2. **Get Your Zotero User ID:**
   - Still on https://www.zotero.org/settings/keys
   - Look for "Your userID for use in API calls"
   - Copy this number

3. **Add to .env file:**
   ```
   ZOTERO_API_KEY=your-api-key-here
   ZOTERO_LIBRARY_ID=your-user-id-here
   ZOTERO_LIBRARY_TYPE=user
   ```

### 3. Install Dependencies

```bash
pip install pyzotero
```

## Usage

### Method 1: Through PhD Agent
```bash
python phd_agent.py
```
Then type: `slack papers`

### Method 2: Standalone Paper Monitor
```bash
python slack_paper_monitor.py
```

Options:
1. **One-time check** - Check recent papers (last 24 hours)
2. **Continuous monitoring** - Check every 30 minutes
3. **Custom time period** - Check specific hours back

### Method 3: Programmatic
```python
from slack_paper_monitor import SlackPaperMonitor
import asyncio

monitor = SlackPaperMonitor()
asyncio.run(monitor.run_once(hours_back=24))
```

## Paper Detection Patterns

The system detects papers from:
- **arXiv**: `arxiv.org/abs/2301.12345`
- **DOI**: `10.1038/s41586-023-12345-6`
- **PubMed**: `pubmed.ncbi.nlm.nih.gov/12345678`
- **bioRxiv**: `biorxiv.org/content/...`
- **Direct PDFs**: Any `.pdf` URL
- **Journal sites**: Nature, Science, Cell, PLOS, IEEE, ACM, Springer, Wiley

## Interactive Features

When papers are found, you'll see:
- Paper title, authors, year, journal
- Message context (who posted, when)
- Option to save to Zotero (y/n)
- Choose Zotero collection
- Skip all remaining papers (s)

## Troubleshooting

### "not_in_channel" Error
- Bot needs to be added to #papers channel
- Use `/invite @camellias_agent` in the channel

### "Zotero connection failed"
- Check API key and user ID in .env
- Verify API key permissions include write access

### No papers detected
- Check that messages contain valid paper URLs
- Test with a known arXiv link: `https://arxiv.org/abs/2301.12345`

### Papers already in Zotero
- System checks for duplicates by DOI and URL
- Shows warning if paper already exists

## Example Workflow

1. Team member posts in #papers:
   ```
   Check out this new paper on LLMs: https://arxiv.org/abs/2401.12345
   Really interesting approach to fine-tuning!
   ```

2. Run `slack papers` command

3. System shows:
   ```
   Paper 1/1
   📄 Title: Efficient Fine-Tuning of Large Language Models
   👥 Authors: Smith, J., Doe, A., Johnson, B.
   📅 Year: 2024
   📖 Journal: arXiv
   🔗 URL: https://arxiv.org/abs/2401.12345

   💬 Posted by: @john_smith
   🕐 Posted at: 2024-01-18 10:30:00

   💾 Save to Zotero? (y/n/s):
   ```

4. Press 'y' to save to your Zotero library

## Advanced Configuration

### Using Group Libraries
If using a Zotero group library instead of personal:
```
ZOTERO_LIBRARY_TYPE=group
ZOTERO_LIBRARY_ID=your-group-id-here
```

### Custom Paper Channel Names
The system looks for channels named "paper" or "papers".
To monitor a different channel, modify the `find_paper_channel()` method in `slack_paper_monitor.py`.

## Support

For issues or questions:
1. Check bot permissions in Slack
2. Verify Zotero API configuration
3. Check logs for detailed error messages
4. Test with known working paper URLs