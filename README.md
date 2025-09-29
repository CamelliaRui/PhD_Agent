# PhD Research Assistant Agent 🎓🤖

An intelligent AI-powered research assistant designed to streamline PhD research workflows by integrating with multiple platforms and automating common academic tasks.

## 🌟 Key Features

### 📚 Literature Management
- **Automated Paper Search**: Search academic papers across ArXiv, Google Scholar, and other databases
- **Smart Paper Analysis**: Extract key insights, methodology, and findings from research papers using AI
- **Zotero Integration**: Seamlessly manage your reference library with automated paper organization and tagging

### 💬 Collaboration & Communication
- **Slack Integration**: Interactive research assistant bot for team collaboration
- **Paper Monitoring**: Real-time alerts for new papers in your research domain
- **Discussion Facilitation**: AI-powered paper discussions and brainstorming sessions

### 📝 Productivity Tools
- **Meeting Agenda Generation**: Automatically generate supervisor meeting agendas based on recent work
- **GitHub Integration**: Track research code progress and commits
- **Notion Integration**: Organize research notes, papers, and ideas in structured databases
- **Weekly Reports**: Automated progress reporting and task tracking
- **DeepWiki Codebase Indexing**: Index and search paper implementation codebases for deep understanding

### 🔗 MCP (Model Context Protocol) Support
- Advanced integration with Claude AI through MCP
- Context-aware assistance for research tasks
- Seamless workflow automation

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- API keys for:
  - Anthropic Claude API
  - Slack (optional)
  - Notion (optional)
  - GitHub (optional)
  - Zotero (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PhD_Agent.git
cd PhD_Agent
```

2. Run the installation script:
```bash
chmod +x install.sh
./install.sh
```

3. Configure your environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## 📖 Usage Examples

### Paper Search and Analysis
```python
from phd_agent import PhdAgent

agent = PhdAgent()
# Search for papers on a specific topic
papers = await agent.search_papers("transformer architectures NLP")
# Analyze a specific paper
analysis = await agent.analyze_paper("https://arxiv.org/abs/...")
```

### Slack Bot for Research Teams
```python
from slack_paper_monitor import SlackPaperMonitor

monitor = SlackPaperMonitor()
# Start monitoring papers and responding to team queries
await monitor.start()
```

### Generate Meeting Agenda
```python
from generate_meeting_agenda import generate_meeting_agenda

# Generate agenda based on last week's work
agenda = generate_meeting_agenda(username="your-github-username", days=7)
print(agenda)
```

### Index and Query Paper Codebases with DeepWiki
```python
from deepwiki_mcp_integration import DeepWikiMCPIntegration

deepwiki = DeepWikiMCPIntegration()

# Index a paper's implementation
result = await deepwiki.index_paper_codebase(
    github_url="https://github.com/huggingface/transformers",
    paper_title="Transformers: State-of-the-Art NLP"
)

# Ask questions about the codebase
answer = await deepwiki.ask_about_codebase(
    repository="huggingface/transformers",
    question="How do I fine-tune BERT for classification?"
)

# Search for specific implementations
results = await deepwiki.search_codebase(
    repository="huggingface/transformers",
    query="attention mechanism"
)
```

## 🏗️ Architecture

The PhD Agent consists of several modular components:

- **Core Agent** (`phd_agent.py`): Main orchestrator for all research tasks
- **Paper Search** (`paper_search.py`): Academic paper discovery across multiple sources
- **Paper Analyzer** (`paper_analyzer.py`): AI-powered paper analysis and summarization
- **Slack Integration** (`slack_mcp_integration.py`, `slack_paper_monitor.py`): Team collaboration features
- **Zotero Integration** (`zotero_mcp_integration.py`): Reference management
- **MCP Integrations** (`mcp_integrations.py`): GitHub and Notion connectivity
- **DeepWiki Integration** (`deepwiki_mcp_integration.py`): Index and search paper implementation codebases
- **Meeting Tools** (`generate_meeting_agenda.py`): Productivity automation

## 🔧 Configuration

### Environment Variables
Create a `.env` file with the following:

```env
# Claude AI
ANTHROPIC_API_KEY=your_api_key

# Slack (optional)
SLACK_BOT_TOKEN=your_bot_token
SLACK_APP_TOKEN=your_app_token

# Notion (optional)
NOTION_API_KEY=your_api_key

# GitHub (optional)
GITHUB_TOKEN=your_token

# Zotero (optional)
ZOTERO_API_KEY=your_api_key
ZOTERO_USER_ID=your_user_id

# DeepWiki (optional)
DEEPWIKI_API_KEY=your_api_key  # For private repos
DEEPWIKI_MAX_CONCURRENCY=5
```

See `.env.example` for a complete template.

## 📚 Documentation

- [Slack & Zotero Setup Guide](SLACK_ZOTERO_SETUP.md) - Detailed setup instructions for Slack bot and Zotero integration

## 🧪 Testing

Run the test suite to verify your setup:

```bash
python test_agent.py
```

This will test:
- Paper search functionality
- AI brainstorming capabilities
- GitHub integration
- Notion database operations
- Weekly report generation

Test DeepWiki integration:

```bash
python test_deepwiki.py
# Or for interactive testing:
python test_deepwiki.py --interactive
```

## 🤝 Contributing

Contributions are welcome! This project is actively being developed as part of PhD research. Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Share research use cases

## 🛠️ Tech Stack

- **Python 3.8+**: Core language
- **Claude AI (Anthropic)**: Advanced AI reasoning
- **Async/Await**: Efficient concurrent operations
- **BeautifulSoup4**: Web scraping
- **ArXiv API**: Academic paper access
- **Slack SDK**: Team collaboration
- **Pyzotero**: Reference management
- **MCP SDK**: Model Context Protocol support

## 📄 License

This project is developed for academic research purposes. Please cite if used in your research work.

## 👨‍🎓 Author

Developed as part of PhD research to enhance academic productivity through AI automation.

## 🚦 Current Status

**Active Development** - New features and integrations are regularly added based on research needs.

### Recent Updates
- ✅ MCP integration for enhanced AI capabilities
- ✅ Slack bot for team collaboration
- ✅ Zotero reference management
- ✅ Meeting agenda automation
- ✅ Multi-source paper search

### Upcoming Features
- 📊 Research progress visualization
- 🔍 Citation network analysis
- 📝 Automated literature review generation
- 🎯 Research goal tracking

---

*Built with ❤️ for PhD researchers, by a PhD researcher*