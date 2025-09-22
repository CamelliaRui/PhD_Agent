#!/bin/bash

echo "🎓 Setting up PhD Agent..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is required but not installed."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Install Claude Code SDK globally
echo "🤖 Installing Claude Code SDK..."
npm install -g @anthropic-ai/claude-code

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys:"
    echo "   - ANTHROPIC_API_KEY (required)"
    echo "   - GITHUB_TOKEN (optional, for GitHub integration)"
    echo "   - NOTION_TOKEN (optional, for Notion integration)"
    echo "   - NOTION_DATABASE_ID (optional, for Notion integration)"
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 To get started:"
echo "   1. Edit .env with your API keys"
echo "   2. Run: python3 phd_agent.py"
echo ""
echo "📚 Example commands:"
echo "   search machine learning interpretability"
echo "   analyze https://arxiv.org/abs/2301.08727"
echo "   brainstorm natural language processing"
echo "   report your_github_username"