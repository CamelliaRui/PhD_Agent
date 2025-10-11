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
- **Conference Schedule Planner** ⭐ NEW (Oct 11, 2025): RAG-based personalized conference scheduling with thesis integration

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

### 🎉 Conference Schedule Planner (NEW - Oct 11, 2025)

The Conference Planner uses **RAG (Retrieval-Augmented Generation)** to create personalized conference schedules based on your research interests, with optional thesis integration for maximum precision.

#### Features
- 📄 **PDF Parsing**: Extracts talks/posters from conference abstract PDFs (ASHG 2025 tested with 4000+ pages)
- 🎯 **Smart Matching**: Semantic similarity matching using ChromaDB and sentence transformers
- 🚫 **Exclusion Filtering**: Filter out wet-lab/clinical work for computational researchers
- 📖 **Thesis Integration**: Upload your unpublished work for highly precise matching (stored locally only)
- ⚡ **Smart Caching**: Parses PDF once, caches talks and embeddings (~2 seconds to regenerate)
- ⚠️ **Conflict Detection**: Identifies overlapping sessions for manual decision-making
- 📅 **Day-by-Day Schedule**: Markdown output organized by day with relevance scores

#### Quick Start

**1. Run the PhD Agent:**
```bash
python phd_agent.py
```

**2. Update your research interests:**
```
📝 You: interests update
```

You'll be prompted for:
- **Research interests** (e.g., "statistical fine-mapping", "single-cell RNA seq")
- **Exclusion topics** (optional, e.g., "wet-lab protocols", "clinical case studies")
- **Thesis/dissertation** (optional, drag & drop your PDF for best matching)

**3. Generate your personalized schedule:**
```
📝 You: conference plan ASHG2025
```

The system will:
- Load cached talks (or parse PDF if first time)
- Load your thesis if provided
- Generate embeddings and match talks to your interests
- Create a personalized schedule with conflict detection

**Output:** `conference/ASHG2025/ashg_schedule.md`

#### Example Workflow

```bash
# Start the agent
$ python phd_agent.py

📝 You: interests update

# Enter your interests
Interest #1: statistical fine-mapping, Bayesian approaches
Interest #2: eQTL, multi-omics, regulatory elements
Interest #3: perturb-seq, CRISPR perturbation
Interest #4: done

# Optional exclusions
Exclude #1: wet-lab protocols and techniques
Exclude #2: clinical case studies without methods
Exclude #3: done

# Optional thesis (drag & drop or type path)
Do you want to add your thesis/dissertation? (y/n): y
Enter path to thesis PDF (or drag file here): /path/to/thesis.pdf
  ✓ Thesis added: thesis.pdf

# Generate schedule
📝 You: conference plan ASHG2025

📦 Loading cached talks (faster!)...
✅ Loaded 323 talks from cache
📊 Talks already indexed in ChromaDB (323 talks)
📖 Loading thesis: thesis.pdf...
✅ Thesis loaded (10000 words)
🎯 Using thesis content for precise matching...
✅ Found 50 relevant talks!
🚫 Filtered out 12 talks matching exclusion criteria

🎊 CONFERENCE SCHEDULE COMPLETE!
  Conference: ASHG2025
  Total talks in PDF: 323
  Relevant to your interests: 50
  Scheduling conflicts: 13

📄 Schedule saved to:
  conference/ASHG2025/ashg_schedule.md
```

#### Advanced Usage

**Programmatic API:**
```python
from conference_planner import ConferencePlanner

# Initialize planner
planner = ConferencePlanner(
    conference_name="ASHG2025",
    conference_dir="./conference/ASHG2025"
)

# Parse PDF (cached after first run)
talks = planner.parse_conference_pdf("path/to/conference.pdf")

# Set research profile
planner.research_interests = [
    "statistical fine-mapping",
    "eQTL analysis",
    "machine learning for genomics"
]
planner.exclusion_topics = [
    "wet-lab protocols",
    "clinical case studies"
]
planner.thesis_path = "/path/to/thesis.pdf"

# Index and find relevant talks
planner.index_talks()
relevant_talks = planner.find_relevant_talks(top_k=50, min_relevance_score=0.3)

# Generate schedule
planner.generate_schedule_markdown(
    relevant_talks,
    "conference/ASHG2025/schedule.md"
)
```

#### Configuration

**Research Interests File** (`research_interests.md`):
```markdown
# Research Interests

*Generated on: 2025-10-11*

## My Research Focus

- statistical fine-mapping, Bayesian approaches
- eQTL, multi-omics, regulatory elements
- perturb-seq, CRISPR perturbation

## Topics to Exclude

*These topics will be filtered out from recommendations:*

- wet-lab protocols and techniques
- clinical case studies without methods

## Unpublished Work (Private)

*Thesis/dissertation stored locally for enhanced matching:*

- Path: `/Users/you/Documents/thesis.pdf`
```

#### How It Works

1. **PDF Parsing**: Custom ASHG parser extracts title, abstract, authors, day, time, location
2. **Caching**: Talks cached as `.ashg2025_talks_cache.pkl`, embeddings in `.chromadb/`
3. **Embedding**: Uses `sentence-transformers` (all-MiniLM-L6-v2) to encode talks and interests
4. **Thesis Integration**: If provided, thesis text (first 10k words) is weighted 2x in the query
5. **RAG Matching**: ChromaDB vector search finds semantically similar talks
6. **Exclusion Filtering**: Keyword-based filtering removes unwanted topics (wet-lab, pure clinical)
7. **Conflict Detection**: Groups talks by time slot, identifies overlaps
8. **Schedule Generation**: Markdown output organized by day with relevance scores

#### Performance

- **First run**: ~60 seconds (parse PDF + generate embeddings)
- **Subsequent runs**: ~2 seconds (load from cache)
- **Memory**: ~500MB for 300+ talks with embeddings
- **Accuracy**: Semantic similarity matching is far superior to keyword search

#### Supported Conferences

Currently optimized for:
- ✅ ASHG (American Society of Human Genetics)
- 🔄 Generic parser for other conference formats (may need customization)

To add a new conference format, implement a custom parser in `conference_planner.py`.

## 🏗️ Architecture

The PhD Agent consists of several modular components:

- **Core Agent** (`phd_agent.py`): Main orchestrator for all research tasks
- **Paper Search** (`paper_search.py`): Academic paper discovery across multiple sources
- **Paper Analyzer** (`paper_analyzer.py`): AI-powered paper analysis and summarization
- **Slack Integration** (`slack_mcp_integration.py`, `slack_paper_monitor.py`): Team collaboration features
- **Zotero Integration** (`zotero_mcp_integration.py`): Reference management
- **MCP Integrations** (`mcp_integrations.py`): GitHub and Notion connectivity
- **DeepWiki Integration** (`deepwiki_mcp_integration.py`): Index and search paper implementation codebases
- **Conference Planner** (`conference_planner.py`): RAG-based personalized conference scheduling
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
- **ChromaDB**: Vector database for RAG
- **Sentence Transformers**: Semantic embeddings
- **PyPDF**: PDF text extraction

## 📄 License

This project is developed for academic research purposes. Please cite if used in your research work.

## 👨‍🎓 Author

Developed as part of PhD research to enhance academic productivity through AI automation.

## 🚦 Current Status

**Active Development** - New features and integrations are regularly added based on research needs.

### Recent Updates
- ✅ **Oct 11, 2025**: Conference Schedule Planner with RAG, thesis integration, and exclusion filtering
- ✅ DeepWiki integration for codebase indexing
- ✅ MCP integration for enhanced AI capabilities
- ✅ Slack bot for team collaboration
- ✅ Zotero reference management
- ✅ Meeting agenda automation
- ✅ Multi-source paper search

### Upcoming Features
- 🎯 Multi-conference support (ISMB, NeurIPS, etc.)
- 📅 Google Calendar integration for conference schedules
- 📊 Research progress visualization
- 🔍 Citation network analysis
- 📝 Automated literature review generation

---

*Built with ❤️ for PhD researchers, by a PhD researcher*