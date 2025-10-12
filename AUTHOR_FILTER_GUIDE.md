# Author-Based Conference Filtering Guide

The conference planner now supports filtering and prioritizing talks by specific authors of interest (e.g., senior authors, collaborators, etc.).

## Features

### 1. **Multi-line Author Parsing**
The parser now correctly extracts all authors from PDF abstracts, even when author lists span multiple lines.

### 2. **Authors of Interest**
Add a list of authors you want to prioritize when planning your conference schedule. The system will:
- **Boost relevance scores** (+0.15) for talks featuring these authors
- **Highlight matching authors** with a ⭐ star in the schedule
- **Show author information** prominently in the output

### 3. **Flexible Matching**
Author matching is case-insensitive and supports partial matches. For example:
- "Pasca" will match "Sergiu P. Pasca"
- "Jonathan Pritchard" will match "Jonathan K. Pritchard"

## How to Use

### Step 1: Add Authors to your Research Interests

Edit your `research_interests.md` file to include an "Authors of Interest" section:

```markdown
# Research Interests

*Generated on: 2025-10-11 21:24:56*

## My Research Focus

- statistical fine-mapping, Bayesian approaches
- eQTL, multi-omics, regulatory elements
- perturb-seq, CRISPR perturbation
- single-cell RNA-seq methods

## Authors of Interest

- Jonathan Pritchard
- Sergiu Pasca
- Nir Yosef
- Sarah Teichmann
- Aviv Regev

## Topics to Exclude

- cancer immunotherapy
- drug development

## Unpublished Work

- Path: `/path/to/your/thesis.pdf`
```

### Step 2: Run the Conference Planner

The planner will automatically load authors of interest and boost talks featuring these researchers:

```python
from conference_planner import ConferencePlanner

planner = ConferencePlanner(
    conference_name="ASHG2025",
    conference_dir="conference/ASHG2025"
)

# Parse conference PDF
planner.parse_conference_pdf("path/to/abstracts.pdf")

# Load research interests (includes authors)
planner.load_research_interests("research_interests.md")

# Index talks
planner.index_talks()

# Find relevant talks (author boosting applied automatically)
relevant_talks = planner.find_relevant_talks(top_k=50, min_relevance_score=0.3)

# Generate schedule
planner.generate_schedule_markdown(relevant_talks, "schedule.md")
```

### Step 3: Review the Generated Schedule

The output will show:

#### In the Header
```markdown
## 👤 Authors of Interest

- Jonathan Pritchard
- Sergiu Pasca
- Nir Yosef
```

#### In Talk Listings
```markdown
### Cell-type-specific eQTL mapping in 1.2M cells

**Type:** 🎤 Talk | **Relevance Score:** 62.45%

**⏰ Time:** 2:00pm – 2:15pm

**👥 Authors:** **⭐ Jonathan K. Pritchard**, Sarah Kim, David Lopez *et al.* (8 total)

**📝 Abstract:**

We performed single-cell eQTL mapping across...
```

Note the ⭐ star highlighting Jonathan K. Pritchard as a matching author!

## Benefits

1. **Prioritize Key Researchers**: Never miss talks by leaders in your field
2. **Track Collaborators**: Easily find talks by colleagues or potential collaborators
3. **Senior Author Focus**: Conference abstracts often list all authors - this helps you focus on the PIs and senior researchers
4. **Score Boosting**: Talks with authors of interest get a +15% relevance boost, helping them rise to the top even if the abstract keywords don't perfectly match

## Tips

- **Last names work well**: "Pritchard" will match "Jonathan K. Pritchard", "J. Pritchard", etc.
- **Full names are more specific**: Use "Jonathan Pritchard" if there are multiple researchers with the same last name
- **Senior authors first**: List the most important researchers at the top of your authors list
- **Mix with interests**: The system combines both topic-based and author-based relevance for optimal results

## Technical Details

### Relevance Calculation

```
Base Score = semantic_similarity(research_interests, talk_abstract)
Author Boost = +0.15 if any matching authors, else 0
Final Score = min(1.0, Base Score + Author Boost)
```

### Author Matching Logic

```python
# Case-insensitive, bidirectional substring matching
author_of_interest.lower() in talk_author.lower()
OR
talk_author.lower() in author_of_interest.lower()
```

This flexible matching ensures you catch variations like:
- "J. K. Pritchard" vs "Jonathan K. Pritchard"
- "Pasca" vs "Sergiu P. Pasca"
- "Teichmann" vs "Sarah A. Teichmann"

## Example Use Cases

### Use Case 1: Following PhD Advisors
Track your advisor's work and related talks to stay current with their research direction.

### Use Case 2: Identifying Collaboration Opportunities
Add researchers whose work complements yours to spot potential collaboration talks.

### Use Case 3: Competitive Intelligence
Monitor talks by competing labs to stay aware of new developments in your space.

### Use Case 4: Career Planning
Follow talks by PIs at institutions you're interested in for postdocs or faculty positions.
