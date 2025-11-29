# ReAct Agent Demo Tasks

These are example tasks you can run with the ReAct agent to showcase observable reasoning.

## 🚀 How to Use

Start the PhD Agent:
```bash
python phd_agent.py
```

Then use the `react` command:
```
📝 You: react [your task here]
```

---

## 📚 Example Tasks

### 1. Paper Search and Discovery

**Simple:**
```
react Find papers on CRISPR gene editing
```

**Multi-step:**
```
react Find papers on statistical fine-mapping and tell me which one has the most citations
```

**Complex:**
```
react Search for papers on transformer models, then find the most influential one and explain why it's important
```

---

### 2. Conference Planning

**Prerequisites:** Must have run `conference plan ASHG2025` first to create cache

**Simple:**
```
react Find relevant talks at ASHG2025 about fine-mapping
```

**With context:**
```
react Get my research interests and find matching talks at ASHG2025
```

**Comparison:**
```
react Compare talks on eQTL analysis vs GWAS fine-mapping at ASHG2025
```

---

### 3. Research Brainstorming

**Idea generation:**
```
react Brainstorm research ideas connecting single-cell genomics with CRISPR screening
```

**Problem solving:**
```
react What are the current challenges in statistical fine-mapping and suggest potential solutions
```

---

### 4. Code Analysis (DeepWiki)

**Prerequisites:** Repository must be indexed first

**Search:**
```
react Search the transformers repository for attention mechanism implementations
```

---

## 🔍 What You'll See

When you run a ReAct task, you'll see the agent's reasoning process:

```
🔄 Starting ReAct agent with observable reasoning...
📋 Task: Find papers on CRISPR

======================================================================
🎯 Task: Find papers on CRISPR
======================================================================

💭 Step 1 - Thought:
   I need to search for academic papers on CRISPR to fulfill this request.

🔧 Action: search_papers
   Input: {'query': 'CRISPR', 'max_results': 3}

👁️  Observation:
   {"count": 3, "papers": [{"title": "CRISPR-Cas9...", ...}]}

🤔 Reflection:
   Successfully found papers on CRISPR. The task is complete.

----------------------------------------------------------------------

💭 Step 2 - Thought:
   Task is complete! I found 3 papers on CRISPR gene editing.

✅ Task Complete!
   Found 3 papers on CRISPR gene editing

======================================================================
✅ Task Status: completed
📊 Steps Taken: 2
💡 Final Result: Found 3 papers on CRISPR gene editing
======================================================================

💾 Reasoning trace saved to: react_trace.json
```

---

## 📊 Understanding the Reasoning Trace

Each step shows:
- **💭 Thought:** What the agent is thinking/planning
- **🔧 Action:** Which tool it decided to use
- **👁️ Observation:** The result of the action
- **🤔 Reflection:** Agent's assessment of progress

The agent automatically decides when to stop based on task completion.

---

## 🎯 Good Tasks for Demos

**For showcasing multi-step reasoning:**
1. "Find papers on X and compare them"
2. "Search for Y and summarize the key findings"
3. "Get my interests and find relevant talks"

**For showcasing tool selection:**
1. Tasks requiring different tools (search + brainstorm)
2. Tasks requiring iteration (search → refine → search again)

**For showcasing completion logic:**
1. Simple tasks (should stop after 1-2 steps)
2. Complex tasks (should use multiple steps)

---

## ⚠️ Known Limitations

1. **API Credits Required:** ReAct agent uses multiple LLM calls (3-5 per step)
2. **Tool Dependencies:** Some tools require prior setup (e.g., conference cache)
3. **Cost:** Multi-step tasks can be expensive (~1000-5000 tokens per task)

---

## 💡 Tips for Best Results

1. **Be specific:** "Find papers on CRISPR" is better than "papers"
2. **Multi-part tasks work well:** "Find X and then do Y"
3. **Check tool availability:** Conference planning needs cache, code search needs indexed repos
4. **Review traces:** Check `react_trace.json` to see full reasoning path

---

## 🐛 Troubleshooting

**Agent doesn't stop:**
- Check if task is too vague
- Review completion logic in traces
- May need to simplify the task

**Tool not found errors:**
- Check if required data exists (conference cache, indexed repos)
- Use `interests update` or `conference plan` first

**API errors:**
- Verify ANTHROPIC_API_KEY is set
- Check credit balance at console.anthropic.com

---

## 📈 Next Steps

After testing ReAct agent:
1. Try increasingly complex multi-step tasks
2. Review reasoning traces for quality
3. Benchmark against direct commands
4. Add custom tools for your specific research workflow
