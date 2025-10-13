"""
Conference Schedule Planner with RAG
Extracts talks/posters from conference PDFs, uses RAG to match with research interests,
and generates personalized schedules with conflict detection.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class ConferenceTalk:
    """Represents a conference talk or poster"""

    def __init__(
        self,
        title: str,
        abstract: str,
        authors: List[str],
        session_type: str,  # "talk" or "poster"
        day: Optional[str] = None,
        time: Optional[str] = None,
        location: Optional[str] = None,
        session_name: Optional[str] = None,
        presentation_id: Optional[str] = None
    ):
        self.title = title
        self.abstract = abstract
        self.authors = authors
        self.session_type = session_type
        self.day = day
        self.time = time
        self.location = location
        self.session_name = session_name
        self.presentation_id = presentation_id or self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID from title"""
        return re.sub(r'[^a-zA-Z0-9]', '_', self.title[:50]).lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'abstract': self.abstract,
            'authors': self.authors,
            'session_type': self.session_type,
            'day': self.day,
            'time': self.time,
            'location': self.location,
            'session_name': self.session_name,
            'presentation_id': self.presentation_id
        }

    def get_searchable_text(self) -> str:
        """Get text for embedding"""
        return f"{self.title}\n{self.abstract}\nAuthors: {', '.join(self.authors)}"


class ConferencePlanner:
    """Main conference planning system with RAG"""

    def __init__(
        self,
        conference_name: str,
        conference_dir: str,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize conference planner

        Args:
            conference_name: Name of the conference (e.g., "ASHG2025")
            conference_dir: Directory containing conference materials
            embedding_model: Sentence transformer model to use
        """
        self.conference_name = conference_name
        self.conference_dir = Path(conference_dir)
        self.embedding_model_name = embedding_model

        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)

        # Initialize ChromaDB with persistent storage
        chroma_dir = self.conference_dir / ".chromadb"
        chroma_dir.mkdir(exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection_name = f"conference_{conference_name.lower()}"
        self.collection = None

        self.talks: List[ConferenceTalk] = []
        self.research_interests: List[str] = []
        self.exclusion_topics: List[str] = []  # Topics to filter out
        self.authors_of_interest: List[str] = []  # Senior authors to prioritize
        self.thesis_path: Optional[str] = None  # Path to unpublished thesis
        self.thesis_text: Optional[str] = None  # Cached thesis text

    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            logger.info(f"Extracted {len(text)} characters from {pdf_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return ""

    def parse_conference_pdf(self, pdf_path: str, use_cache: bool = True) -> List[ConferenceTalk]:
        """
        Parse conference PDF to extract talks and posters

        This is a template method that should be customized based on the
        specific format of your conference PDF.

        Args:
            pdf_path: Path to PDF file
            use_cache: If True, use cached talks if available

        Returns:
            List of ConferenceTalk objects
        """
        import pickle
        from pathlib import Path

        # Check for cached talks
        cache_file = Path(pdf_path).parent / f".{self.conference_name.lower()}_talks_cache.pkl"

        if use_cache and cache_file.exists():
            try:
                # Check if cache is newer than PDF
                pdf_mtime = Path(pdf_path).stat().st_mtime
                cache_mtime = cache_file.stat().st_mtime

                if cache_mtime >= pdf_mtime:
                    logger.info(f"Loading talks from cache: {cache_file}")
                    print(f"📦 Loading cached talks (faster!)...")
                    with open(cache_file, 'rb') as f:
                        talks = pickle.load(f)
                    self.talks = talks
                    logger.info(f"Loaded {len(talks)} talks from cache")
                    print(f"✅ Loaded {len(talks)} talks from cache")
                    return talks
                else:
                    logger.info("Cache outdated, re-parsing PDF")
            except Exception as e:
                logger.warning(f"Could not load cache: {e}")

        # Parse PDF (cache miss or disabled)
        print(f"📄 Parsing PDF (this may take a minute, but will be cached)...")
        text = self.extract_pdf_text(pdf_path)

        # Use ASHG-specific parser if this is ASHG conference
        if "ASHG" in self.conference_name.upper():
            talks = self._parse_ashg_abstracts(text)
        else:
            # Fall back to generic parser for other conferences
            talks = self._parse_talks_generic(text)

        self.talks = talks
        logger.info(f"Parsed {len(talks)} talks/posters from PDF")

        # Save to cache
        if use_cache:
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(talks, f)
                logger.info(f"Saved talks to cache: {cache_file}")
                print(f"💾 Cached talks for faster future use")
            except Exception as e:
                logger.warning(f"Could not save cache: {e}")

        return talks

    def _parse_talks_generic(self, text: str) -> List[ConferenceTalk]:
        """
        Generic parser for conference abstracts

        This is a placeholder that attempts to extract basic structure.
        Should be customized for specific conference formats.
        """
        talks = []

        # Split by common section markers
        # This is a very basic parser - needs customization
        sections = re.split(r'\n(?=\d+\.\s+[A-Z])', text)

        for section in sections:
            # Try to extract title, authors, abstract
            lines = section.strip().split('\n')
            if len(lines) < 3:
                continue

            # Very basic extraction - customize based on actual format
            title = lines[0].strip()
            authors_line = lines[1].strip() if len(lines) > 1 else ""
            abstract = '\n'.join(lines[2:]).strip() if len(lines) > 2 else ""

            # Extract authors (assuming comma-separated)
            authors = [a.strip() for a in authors_line.split(',') if a.strip()]

            if title and abstract:
                talk = ConferenceTalk(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    session_type="talk"  # Default to talk
                )
                talks.append(talk)

        return talks

    def _parse_ashg_abstracts(self, text: str) -> List[ConferenceTalk]:
        """
        ASHG-specific parser for conference abstracts

        Uses "Authors:" as the primary marker since both talks and posters have this field.
        Platform talks have "Subsession Time:", posters have "Session:" or session type info.
        """
        talks = []

        # Split by "Authors:" markers to find all abstracts (talks and posters)
        sections = []
        lines = text.split('\n')

        authors_found = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('Authors:'):
                authors_found += 1
                # Look backwards for title (usually 1-5 lines before)
                title_lines = []
                for j in range(i-1, max(0, i-8)-1, -1):
                    prev_line = lines[j].strip()

                    # Stop at blank lines
                    if not prev_line:
                        if title_lines:  # Only stop if we already have title
                            break
                        else:
                            continue  # Skip blank lines before title

                    # Skip metadata fields (but keep looking for title)
                    if prev_line.startswith(('Location:', 'Subsession Time:', 'Session Time:')):
                        continue

                    # Stop at section headers
                    if (prev_line.startswith(('ASHG', 'PgmNr', 'indicates', 'Table of Contents')) or
                        prev_line.startswith('Session ') and ':' in prev_line):  # "Session 10:" etc
                        break

                    # Skip header/footer junk and table of contents entries
                    if any(word in prev_line.lower() for word in ['table of contents', 'click on', 'page ', ' as of ']):
                        continue

                    # Skip table of contents entries (have many dots)
                    if prev_line.count('.') > 5 or '...' in prev_line:
                        continue

                    # Skip lines that are mostly punctuation/formatting
                    alpha_chars = sum(c.isalpha() for c in prev_line)
                    if len(prev_line) > 0 and alpha_chars / len(prev_line) < 0.5:
                        continue

                    # Likely a title if:
                    # - Not a metadata field
                    # - Has reasonable length (> 15 chars)
                    # - Not obviously abstract text
                    # - Not truncated mid-sentence
                    if len(prev_line) > 15:
                        # Exclude obvious abstract text (contains first-person or methodological language)
                        is_abstract_text = (
                            prev_line.endswith('.') and
                            any(word in prev_line.lower() for word in [' we ', ' our ', ' were ', ' was ', ' this study', 'background:', 'methods:', 'results:', 'conclusion:'])
                        )

                        # Exclude fragments that start mid-sentence (lowercase first letter)
                        is_fragment = prev_line[0].islower()

                        if not is_abstract_text and not is_fragment:
                            title_lines.insert(0, prev_line)
                            if len(title_lines) >= 2:  # Max 2 lines for title
                                break

                    # Stop after we have at least one title line
                    if title_lines and (len(prev_line) < 10 or prev_line.startswith(('Abstract:', 'Authors:'))):
                        break

                # Build section with extracted title + context
                title = ' '.join(title_lines) if title_lines else None

                if title:
                    section_lines = [title]  # Start with extracted title

                    # Include metadata (session, time, location) right before Authors
                    for j in range(max(0, i-5), i):
                        line_text = lines[j].strip()
                        if line_text and (line_text.startswith(('Session', 'Location:', 'Subsession Time:')) or
                                          'Session' in line_text):
                            section_lines.append(lines[j])

                    # Include from Authors onwards until next Authors: or end
                    for j in range(i, len(lines)):
                        next_line = lines[j].strip()

                        # Stop at next abstract
                        if j > i and next_line.startswith('Authors:'):
                            break

                        section_lines.append(lines[j])

                        # Stop after we have enough content
                        if j - i > 100:
                            break

                    section_text = '\n'.join(section_lines)
                    sections.append(section_text)
                else:
                    logger.debug(f"Skipped abstract at line {i} - no valid title found")

        logger.info(f"Found {authors_found} 'Authors:' markers, extracted {len(sections)} potential abstracts")

        # Parse each section
        for section in sections:
            try:
                talk = self._parse_single_ashg_abstract_v2(section)
                if talk:
                    talks.append(talk)
            except Exception as e:
                logger.debug(f"Failed to parse section: {e}")
                continue

        logger.info(f"ASHG parser extracted {len(talks)} talks/posters")
        return talks
    
    def _parse_single_ashg_abstract_v2(self, section: str) -> Optional[ConferenceTalk]:
        """Parse a single ASHG abstract section (v2 - improved)"""
        lines = section.strip().split('\n')
        if len(lines) < 3:
            return None

        # First line should be the title
        title = lines[0].strip()

        # Find the subsession time line
        day = None
        time = None
        location = None
        authors_line = None
        abstract_text = None
        session_type = "talk"  # Default to talk

        # Detect session type from the entire section text
        section_lower = section.lower()
        if any(keyword in section_lower for keyword in ['poster', 'poster session', 'poster presentation', 'pgmnr']):
            session_type = "poster"
        elif any(keyword in section_lower for keyword in ['platform', 'oral', 'invited', 'plenary', 'subsession time']):
            session_type = "talk"
        else:
            # Default to poster if no clear indicator (most abstracts are posters)
            session_type = "poster"

        for i, line in enumerate(lines):
            line = line.strip()

            # Extract timing information (for both talks and posters)
            if 'Subsession Time:' in line or 'Session:' in line:
                day_time_match = re.search(r'(\w+, \w+ \d+) at ([\d:apm –-]+)', line)
                if day_time_match:
                    day = day_time_match.group(1)
                    time = day_time_match.group(2)
                else:
                    # Try alternate format: "Session: Day"
                    day_match = re.search(r'(?:Session|Subsession Time):\s*(.+?)(?:$|at)', line)
                    if day_match:
                        day = day_match.group(1).strip()
                continue

            # Extract location
            if line.startswith('Location:'):
                location = line[9:].strip()  # Remove "Location:" prefix
                continue

            # Look for authors line (may span multiple lines)
            if line.startswith('Authors:'):
                author_lines = [line[8:].strip()]  # Remove "Authors:" prefix from first line
                # Collect continuation lines until we hit another field
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    # Stop at blank lines or next field
                    if not next_line or next_line.startswith(('Abstract:', 'Location:', 'Subsession')):
                        break
                    # If line doesn't start with a field marker, it's a continuation
                    if not any(next_line.startswith(field) for field in ['Authors:', 'Abstract:', 'Location:']):
                        author_lines.append(next_line)
                    else:
                        break
                authors_line = ' '.join(author_lines)
                continue

            # Look for abstract
            if line.startswith('Abstract:'):
                # Collect all remaining lines as abstract
                abstract_lines = [line[9:].strip()]  # Remove "Abstract:" prefix
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith(('Subsection Time:', 'Authors:')):
                        abstract_lines.append(next_line)
                abstract_text = ' '.join(abstract_lines)
                break
        
        # Parse authors
        authors = []
        if authors_line:
            # Split by comma, but be careful about affiliations in parentheses
            author_parts = []
            current_part = ""
            paren_count = 0
            
            for char in authors_line:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == ',' and paren_count == 0:
                    author_parts.append(current_part.strip())
                    current_part = ""
                    continue
                current_part += char
            
            if current_part.strip():
                author_parts.append(current_part.strip())
            
            # Extract just names (before parentheses)
            for part in author_parts:
                name_match = re.match(r'^([^(]+)', part.strip())
                if name_match:
                    name = name_match.group(1).strip()
                    if name and len(name) > 2:  # Valid name
                        authors.append(name)

        # Only create talk if we have essential components
        if title and abstract_text and len(abstract_text) > 50:
            return ConferenceTalk(
                title=title,
                abstract=abstract_text,
                authors=authors,
                session_type=session_type,  # Detected from section text
                day=day,
                time=time,
                location=location
            )

        return None

    def _parse_single_ashg_abstract(self, chunk: str) -> Optional[ConferenceTalk]:
        """Parse a single ASHG abstract chunk"""
        lines = chunk.strip().split('\n')
        if len(lines) < 3:
            return None

        # Extract timing information (first line after split)
        time_line = lines[0].strip()
        day_time_match = re.search(r'(\w+, \w+ \d+) at ([\d:apm –-]+)', time_line)
        day = day_time_match.group(1) if day_time_match else None
        time = day_time_match.group(2) if day_time_match else None

        # Find title, authors, location, and abstract
        title = None
        location = None
        authors_line = None
        abstract_text = None
        
        # Look for patterns in order
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip headers and short lines
            if (not line or 
                line.startswith('ASHG') or 
                line.startswith('indicates') or
                len(line) < 10):
                i += 1
                continue
            
            # Look for authors line first
            if line.startswith('Authors:'):
                authors_line = line[8:].strip()  # Remove "Authors:" prefix
                i += 1
                continue

            # Look for location
            if line.startswith('Location:'):
                location = line[9:].strip()  # Remove "Location:" prefix
                i += 1
                continue

            # Look for abstract
            if line.startswith('Abstract:'):
                # Collect all remaining lines as abstract
                abstract_lines = [line[9:].strip()]  # Remove "Abstract:" prefix
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    # Stop if we hit another abstract or structural element
                    if (next_line.startswith(('Abstract:', 'Authors:', 'Session', 'Subsession Time:')) or
                        (next_line and len(next_line) > 50 and 
                         any(keyword in next_line.lower() for keyword in ['university', 'institute', 'hospital']))):
                        break
                    if next_line:
                        abstract_lines.append(next_line)
                abstract_text = ' '.join(abstract_lines)
                break
            
            # If we haven't found a title yet and this looks like one
            # Title usually comes before Authors line
            if (not title and not authors_line and
                not line.startswith(('Session', 'Location:', 'Time:', 'Subsession')) and
                30 <= len(line) <= 300 and
                not line.lower().startswith(('background:', 'methods:', 'results:', 'conclusion:')) and
                # Avoid lines that look like author lists (contain parentheses with institutions)
                not (('(' in line and ')' in line) and ('university' in line.lower() or 'institute' in line.lower()))):
                title = line
                i += 1
                continue
            
            i += 1
        
        # If no title found yet, look for it more broadly
        if not title:
            for line in lines[1:]:
                line = line.strip()
                if (line and 
                    not line.startswith(('Authors:', 'Abstract:', 'Session', 'Location:', 'Time:', 'ASHG', 'indicates')) and
                    20 <= len(line) <= 300 and
                    not (('(' in line and ')' in line) and ('university' in line.lower() or 'institute' in line.lower()))):
                    title = line
                    break
        
        # Parse authors
        authors = []
        if authors_line:
            # Split by comma, but be careful about affiliations in parentheses
            author_parts = []
            current_part = ""
            paren_count = 0
            
            for char in authors_line:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == ',' and paren_count == 0:
                    author_parts.append(current_part.strip())
                    current_part = ""
                    continue
                current_part += char
            
            if current_part.strip():
                author_parts.append(current_part.strip())
            
            # Extract just names (before parentheses)
            for part in author_parts:
                name_match = re.match(r'^([^(]+)', part.strip())
                if name_match:
                    name = name_match.group(1).strip()
                    if name and len(name) > 2:  # Valid name
                        authors.append(name)
        
        # Only create talk if we have essential components
        if title and abstract_text and len(abstract_text) > 50:
            return ConferenceTalk(
                title=title,
                abstract=abstract_text,
                authors=authors,
                session_type="talk",  # ASHG abstracts are typically talks
                day=day,
                time=time,
                location=location
            )

        return None

    def load_research_interests(self, interests_file: str) -> List[str]:
        """Load research interests and exclusion topics from markdown file"""
        try:
            with open(interests_file, 'r') as f:
                content = f.read()

            # Extract sections
            interests = []
            exclusions = []
            authors_of_interest = []
            thesis_path = None
            current_section = None

            for line in content.split('\n'):
                line_stripped = line.strip()

                # Detect sections
                if line_stripped.startswith('## My Research Focus'):
                    current_section = 'interests'
                    continue
                elif line_stripped.startswith('## Topics to Exclude'):
                    current_section = 'exclusions'
                    continue
                elif line_stripped.startswith('## Authors of Interest'):
                    current_section = 'authors'
                    continue
                elif line_stripped.startswith('## Unpublished Work'):
                    current_section = 'thesis'
                    continue
                elif line_stripped.startswith('#'):
                    current_section = None
                    continue

                # Extract bullet points
                if line_stripped and line_stripped.startswith('-'):
                    item = re.sub(r'^[-*+]\s+', '', line_stripped)
                    if item and not item.startswith('*'):  # Skip markdown emphasis
                        if current_section == 'interests':
                            interests.append(item)
                        elif current_section == 'exclusions':
                            exclusions.append(item)
                        elif current_section == 'authors':
                            authors_of_interest.append(item.strip())
                        elif current_section == 'thesis' and item.startswith('Path:'):
                            # Extract path from "Path: `path/to/file`"
                            thesis_path = item.replace('Path:', '').strip('` ')

            self.research_interests = interests
            self.exclusion_topics = exclusions
            self.authors_of_interest = authors_of_interest
            self.thesis_path = thesis_path
            logger.info(f"Loaded {len(interests)} interests, {len(exclusions)} exclusions, {len(authors_of_interest)} authors, thesis: {thesis_path is not None}")
            return interests

        except FileNotFoundError:
            logger.warning(f"Research interests file not found: {interests_file}")
            return []

    def prompt_research_interests(self, interests_file: str = "research_interests.md") -> List[str]:
        """
        Interactively prompt user for research interests
        Shows existing interests and allows adding or starting fresh

        Args:
            interests_file: Path to check for existing interests

        Returns list of research interest strings
        """
        from pathlib import Path

        print("\n" + "="*60)
        print("🎯 RESEARCH INTERESTS SETUP")
        print("="*60)

        # Check for existing interests
        existing_interests = []
        interests_path = Path(interests_file)

        if interests_path.exists():
            try:
                existing_interests = self.load_research_interests(str(interests_path))
                if existing_interests:
                    print("\n📚 Current research interests found:")
                    for i, interest in enumerate(existing_interests, 1):
                        # Filter out placeholder entries
                        if interest.strip() and interest.strip().upper() != 'NA':
                            print(f"  {i}. {interest}")

                    print("\n" + "-"*60)
                    choice = input("\nDo you want to (a)dd to these, (r)eplace them, or (k)eep as-is? [a/r/k]: ").strip().lower()
                    print("-"*60)

                    if choice == 'k':
                        print(f"\n✅ Keeping existing {len(existing_interests)} interests.\n")
                        self.research_interests = existing_interests
                        interests = existing_interests
                        skip_interest_input = True  # Skip to exclusions/thesis
                    elif choice == 'r':
                        print("\n🔄 Starting fresh...\n")
                        interests = []
                        skip_interest_input = False
                    else:  # default to 'add'
                        print(f"\n➕ Adding to existing interests...\n")
                        # Filter out NA entries
                        interests = [i for i in existing_interests if i.strip() and i.strip().upper() != 'NA']
                        skip_interest_input = False
                else:
                    interests = []
                    skip_interest_input = False
            except Exception as e:
                logger.debug(f"Could not load existing interests: {e}")
                interests = []
                skip_interest_input = False
        else:
            interests = []
            skip_interest_input = False

        # Show instructions (only if not skipping)
        if not skip_interest_input and not interests:
            print("\nPlease describe your research interests for conference planning.")
            print("This will help match talks and posters relevant to your work.")
            print("\n💡 Examples:")
            print("  - CRISPR gene editing and therapeutic applications")
            print("  - Population genetics and evolutionary biology")
            print("  - Cancer genomics and precision medicine")
            print("  - Machine learning for genomic prediction")
            print("  - Statistical fine-mapping for genetic data")
            print("  - eQTLs, QTLs, and regulatory elements")
        elif not skip_interest_input:
            print("\n💡 Add more interests to complement the ones above.")

        # Only prompt for new interests if not skipping
        if not skip_interest_input:
            print("\nEnter your interests one per line. Type 'done' when finished.")
            print("-"*60 + "\n")

            start_num = len(interests) + 1
            while True:
                interest = input(f"Interest #{len(interests) + 1}: ").strip()

                if interest.lower() == 'done':
                    if not interests:
                        print("\n⚠️  Please enter at least one research interest.")
                        continue
                    break

                if interest and interest.upper() != 'NA':
                    interests.append(interest)
                    print(f"  ✓ Added: {interest}")

            self.research_interests = interests
            print(f"\n✅ Total: {len(interests)} research interests!\n")
        else:
            # Already set above when 'k' was chosen
            print(f"✅ Using {len(interests)} existing interests\n")

        # Now ask for exclusion topics
        print("\n" + "="*60)
        print("🚫 EXCLUSION TOPICS (Optional)")
        print("="*60)
        print("\n💡 To improve filtering, specify topics you want to AVOID:")
        print("  For computational/statistical genetics, you might exclude:")
        print("  - Pure wet-lab protocols and techniques")
        print("  - Clinical case studies without methods")
        print("  - Traditional genetics without computational aspects")
        print("  - Purely experimental molecular biology")
        print("\nEnter exclusion topics one per line. Type 'done' or 'skip' to finish.")
        print("-"*60 + "\n")

        exclusions = []
        while True:
            exclusion = input(f"Exclude #{len(exclusions) + 1} (or 'done'/'skip'): ").strip()

            if exclusion.lower() in ['done', 'skip', '']:
                break

            if exclusion:
                exclusions.append(exclusion)
                print(f"  ✓ Will exclude: {exclusion}")

        self.exclusion_topics = exclusions
        if exclusions:
            print(f"\n✅ Will filter out {len(exclusions)} exclusion topics!\n")
        else:
            print(f"\n⏭️  No exclusions set (will show all relevant talks)\n")

        # Ask about thesis/dissertation (advanced feature)
        print("\n" + "="*60)
        print("📄 UNPUBLISHED WORK (Optional - Advanced)")
        print("="*60)
        print("\n💡 Upload your thesis/dissertation for BEST matching:")
        print("  - Uses your actual research content for semantic matching")
        print("  - Stored locally (never uploaded anywhere)")
        print("  - Finds talks most relevant to YOUR specific work")
        print("  - More accurate than keyword matching")
        print("\n⚠️  Only provide drafts/unpublished work you're comfortable storing locally")
        print("-"*60)

        thesis_response = input("\nDo you want to add your thesis/dissertation? (y/n): ").strip().lower()

        if thesis_response == 'y':
            thesis_path_input = input("Enter path to thesis PDF (or drag file here): ").strip()

            if thesis_path_input and thesis_path_input.lower() != 'skip':
                from pathlib import Path
                import codecs

                # Clean up path (handles drag-and-drop with escape characters)
                # Strip quotes (single and double)
                thesis_path_input = thesis_path_input.strip('\'"')

                # Decode escape sequences (e.g., \' becomes ')
                try:
                    thesis_path_input = codecs.decode(thesis_path_input, 'unicode_escape')
                except:
                    pass  # If decode fails, use as-is

                # Expand ~ and resolve to absolute path
                thesis_path = Path(thesis_path_input).expanduser().resolve()

                if thesis_path.exists() and thesis_path.suffix.lower() == '.pdf':
                    self.thesis_path = str(thesis_path)
                    print(f"  ✓ Thesis added: {thesis_path.name}")
                    print(f"  📍 Will use for enhanced matching")
                else:
                    print(f"  ⚠️  File not found: {thesis_path}")
                    print(f"  ⚠️  Please check the path and try again")
                    self.thesis_path = None
            else:
                self.thesis_path = None
        else:
            self.thesis_path = None

        if self.thesis_path:
            print(f"\n✅ Thesis added for enhanced RAG matching!\n")
        else:
            print(f"\n⏭️  No thesis added (will use interests only)\n")

        return interests

    def save_research_interests(self, output_file: str):
        """Save research interests, exclusion topics, and thesis info to markdown file"""
        if not self.research_interests:
            logger.warning("No research interests to save")
            return

        content = "# Research Interests\n\n"
        content += f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        content += "## My Research Focus\n\n"

        for interest in self.research_interests:
            content += f"- {interest}\n"

        # Add exclusion topics if any
        if self.exclusion_topics:
            content += "\n## Topics to Exclude\n\n"
            content += "*These topics will be filtered out from recommendations:*\n\n"
            for exclusion in self.exclusion_topics:
                content += f"- {exclusion}\n"

        # Add thesis info if provided
        if self.thesis_path:
            content += "\n## Unpublished Work (Private)\n\n"
            content += f"*Thesis/dissertation stored locally for enhanced matching:*\n\n"
            content += f"- Path: `{self.thesis_path}`\n"

        with open(output_file, 'w') as f:
            f.write(content)

        logger.info(f"Saved research interests to {output_file}")
        print(f"💾 Research interests saved to: {output_file}")

    def load_thesis_text(self) -> Optional[str]:
        """
        Load and extract text from thesis PDF
        Caches the result to avoid repeated extraction

        Returns:
            Thesis text or None if not available
        """
        if not self.thesis_path:
            return None

        # Return cached text if available
        if self.thesis_text:
            return self.thesis_text

        try:
            from pathlib import Path

            thesis_file = Path(self.thesis_path)
            if not thesis_file.exists():
                logger.warning(f"Thesis file not found: {self.thesis_path}")
                return None

            logger.info(f"Loading thesis from: {self.thesis_path}")
            print(f"📖 Loading thesis: {thesis_file.name}...")

            # Extract text from PDF
            thesis_text = self.extract_pdf_text(str(thesis_file))

            if thesis_text:
                # Take first 10000 words to avoid overloading (typically intro + methods + results)
                words = thesis_text.split()[:10000]
                thesis_text = ' '.join(words)

                self.thesis_text = thesis_text
                logger.info(f"Loaded {len(thesis_text)} characters from thesis")
                print(f"✅ Thesis loaded ({len(words)} words)")
                return thesis_text
            else:
                logger.warning("Could not extract text from thesis")
                return None

        except Exception as e:
            logger.error(f"Error loading thesis: {e}")
            print(f"⚠️  Could not load thesis: {e}")
            return None

    def index_talks(self):
        """Index all talks in ChromaDB for RAG"""
        if not self.talks:
            logger.error("No talks to index. Parse PDF first.")
            return

        # Create or get collection
        try:
            self.collection = self.chroma_client.get_collection(self.collection_name)
            existing_count = self.collection.count()
            logger.info(f"Found existing collection: {self.collection_name} with {existing_count} items")

            # Check if already indexed
            if existing_count == len(self.talks):
                print(f"📊 Talks already indexed in ChromaDB ({existing_count} talks)")
                logger.info(f"Collection already has correct count, skipping indexing")
                return
            elif existing_count > 0:
                # Different count, delete and recreate
                logger.info(f"Collection has {existing_count} items but we have {len(self.talks)} talks, recreating...")
                self.chroma_client.delete_collection(self.collection_name)
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"conference": self.conference_name}
                )
        except:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"conference": self.conference_name}
            )
            logger.info(f"Created new collection: {self.collection_name}")

        # Prepare documents for embedding
        documents = []
        metadatas = []
        ids = []

        for idx, talk in enumerate(self.talks):
            documents.append(talk.get_searchable_text())

            # Convert to dict and make ChromaDB-compatible (no lists, no None)
            metadata = talk.to_dict()
            metadata['authors'] = ', '.join(talk.authors) if talk.authors else ''

            # Remove None values - ChromaDB doesn't accept them
            metadata = {k: v for k, v in metadata.items() if v is not None}

            # Convert remaining None to empty strings
            for key in ['day', 'time', 'location', 'session_name']:
                if key not in metadata:
                    metadata[key] = ''

            metadatas.append(metadata)
            # Use index to ensure unique IDs (presentation_id may be duplicate or None)
            ids.append(f"{self.conference_name.lower()}_{idx}")

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} talks...")
        print(f"🔍 Generating embeddings for {len(documents)} talks (one-time, will be cached)...")
        embeddings = self.embedder.encode(documents, show_progress_bar=True)

        # Add to ChromaDB
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"✅ Indexed {len(documents)} talks in ChromaDB")

    def should_exclude_talk(self, talk: ConferenceTalk) -> bool:
        """
        Determine if a talk should be excluded based on exclusion topics

        Args:
            talk: The ConferenceTalk to evaluate

        Returns:
            True if talk should be excluded, False otherwise
        """
        if not self.exclusion_topics:
            return False

        # Combine title and abstract for analysis
        text = f"{talk.title} {talk.abstract}".lower()

        # Define computational/statistical indicators
        computational_indicators = [
            'computational', 'statistical', 'algorithm', 'machine learning', 'deep learning',
            'model', 'modeling', 'prediction', 'bioinformatics', 'simulation', 'software',
            'bayesian', 'regression', 'neural network', 'random forest', 'clustering',
            'dimensionality reduction', 'feature selection', 'cross-validation',
            'likelihood', 'inference', 'estimation', 'pipeline', 'workflow', 'framework',
            'database', 'tool', 'method development', 'novel method', 'approach'
        ]

        # Define wet-lab/clinical indicators (things to potentially exclude)
        wetlab_indicators = [
            'pipetting', 'western blot', 'immunostaining', 'cell culture',
            'gel electrophoresis', 'cloning', 'transfection', 'microscopy',
            'staining', 'histology', 'immunohistochemistry', 'pcr protocol',
            'purification', 'extraction protocol', 'laboratory technique'
        ]

        clinical_indicators = [
            'case report', 'case series', 'clinical trial enrollment',
            'patient recruitment', 'clinical management', 'treatment protocol',
            'surgical procedure', 'diagnostic criteria', 'clinical presentation'
        ]

        # Count indicators
        comp_count = sum(1 for indicator in computational_indicators if indicator in text)
        wetlab_count = sum(1 for indicator in wetlab_indicators if indicator in text)
        clinical_count = sum(1 for indicator in clinical_indicators if indicator in text)

        # Check exclusion topics against text
        exclusion_match_count = 0
        for exclusion_topic in self.exclusion_topics:
            exclusion_lower = exclusion_topic.lower()

            # Extract keywords from exclusion topic
            exclusion_keywords = exclusion_lower.split()

            # Check if multiple keywords from exclusion appear
            matches = sum(1 for keyword in exclusion_keywords if len(keyword) > 3 and keyword in text)

            if matches >= 2 or exclusion_lower in text:
                exclusion_match_count += 1

        # Exclusion logic: Exclude if:
        # 1. Strong exclusion match AND no computational signals
        # 2. High wet-lab indicators AND low computational indicators
        # 3. Clinical without methods content

        if exclusion_match_count >= 2 and comp_count == 0:
            return True

        if wetlab_count >= 3 and comp_count <= 1:
            return True

        if clinical_count >= 2 and comp_count == 0:
            return True

        # Check for specific exclusion phrases
        pure_wetlab_phrases = [
            'experimental protocol', 'laboratory protocol', 'wet lab',
            'bench protocol', 'pipetting technique'
        ]

        for phrase in pure_wetlab_phrases:
            if phrase in text and comp_count == 0:
                return True

        return False

    def find_relevant_talks(
        self,
        top_k: int = 50,
        min_relevance_score: float = 0.3
    ) -> List[Tuple[ConferenceTalk, float]]:
        """
        Find talks relevant to research interests using RAG

        Returns list of (talk, relevance_score) tuples sorted by relevance
        """
        if not self.collection:
            raise ValueError("Collection not initialized. Call index_talks() first.")

        if not self.research_interests:
            raise ValueError("No research interests defined.")

        # Combine research interests into query
        query_text = " ".join(self.research_interests)

        # Add thesis content if available (weighted heavily)
        thesis_text = self.load_thesis_text()
        if thesis_text:
            logger.info("Using thesis content for enhanced matching")
            print(f"🎯 Using thesis content for precise matching...")
            # Weight thesis content more heavily by repeating it
            query_text = f"{thesis_text} {thesis_text} {query_text}"

        # Generate query embedding
        query_embedding = self.embedder.encode(query_text)

        # Query ChromaDB - fetch more since we'll filter some out
        fetch_count = min(top_k * 3, len(self.talks)) if self.exclusion_topics else min(top_k, len(self.talks))

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=fetch_count
        )

        # Parse results
        relevant_talks = []
        excluded_count = 0

        for i, (metadata, distance) in enumerate(
            zip(results['metadatas'][0], results['distances'][0])
        ):
            # Convert distance to similarity score (1 - normalized distance)
            # ChromaDB uses L2 distance, convert to similarity
            similarity = 1 / (1 + distance)

            if similarity >= min_relevance_score:
                # Convert authors back from string to list
                metadata_copy = metadata.copy()
                if isinstance(metadata_copy['authors'], str):
                    metadata_copy['authors'] = [
                        a.strip() for a in metadata_copy['authors'].split(',') if a.strip()
                    ]
                talk = ConferenceTalk(**metadata_copy)

                # Boost score for authors of interest
                author_boost = 0.0
                matching_authors = []
                if self.authors_of_interest and talk.authors:
                    for author_of_interest in self.authors_of_interest:
                        # Tokenize author name (split by spaces, periods, commas)
                        interest_tokens = [t.lower().strip('.,') for t in author_of_interest.split() if len(t.strip('.,')) > 1]

                        for talk_author in talk.authors:
                            talk_tokens = [t.lower().strip('.,') for t in talk_author.split() if len(t.strip('.,')) > 1]

                            # Match if all non-initial tokens from interest appear in talk author
                            # (handles middle initials, suffixes, etc.)
                            if all(token in talk_tokens for token in interest_tokens):
                                matching_authors.append(talk_author)
                                author_boost = 0.15  # Significant boost for author match
                                break

                # Apply boost to similarity
                boosted_similarity = min(1.0, similarity + author_boost)

                # Store matching authors as metadata (for display later)
                if matching_authors:
                    talk._matching_authors = matching_authors  # Store for markdown output
                    logger.info(f"Author match: {talk.title} - {matching_authors}")

                # Apply exclusion filter
                if not self.should_exclude_talk(talk):
                    relevant_talks.append((talk, boosted_similarity))
                    if len(relevant_talks) >= top_k:
                        break
                else:
                    excluded_count += 1
                    logger.debug(f"Excluded talk: {talk.title}")

        if excluded_count > 0:
            logger.info(f"Found {len(relevant_talks)} relevant talks after filtering out {excluded_count} excluded topics")
            print(f"🚫 Filtered out {excluded_count} talks matching exclusion criteria")
        else:
            logger.info(f"Found {len(relevant_talks)} relevant talks (threshold: {min_relevance_score})")

        return relevant_talks

    def detect_conflicts(
        self,
        talks: List[Tuple[ConferenceTalk, float]]
    ) -> Dict[str, List[Tuple[ConferenceTalk, float]]]:
        """
        Detect scheduling conflicts where multiple interesting talks overlap

        Returns dict mapping time slots to conflicting talks
        """
        conflicts = {}

        # Group by day and time
        time_slots = {}
        for talk, score in talks:
            if talk.day and talk.time:
                time_key = f"{talk.day}_{talk.time}"
                if time_key not in time_slots:
                    time_slots[time_key] = []
                time_slots[time_key].append((talk, score))

        # Find slots with multiple talks
        for time_key, slot_talks in time_slots.items():
            if len(slot_talks) > 1:
                conflicts[time_key] = slot_talks

        return conflicts

    def generate_schedule_markdown(
        self,
        relevant_talks: List[Tuple[ConferenceTalk, float]],
        output_file: str,
        include_conflicts: bool = True
    ):
        """
        Generate markdown schedule organized by day
        """
        # Sort talks by day and time
        sorted_talks = sorted(
            relevant_talks,
            key=lambda x: (x[0].day or "Unknown", x[0].time or "Unknown", -x[1])
        )

        # Detect conflicts
        conflicts = self.detect_conflicts(relevant_talks) if include_conflicts else {}

        # Generate markdown
        md = f"# {self.conference_name} - Personalized Schedule\n\n"
        md += f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        md += f"**Total Relevant Sessions: {len(relevant_talks)}**\n\n"

        if conflicts:
            md += f"⚠️ **{len(conflicts)} scheduling conflicts detected** (marked with 🔴)\n\n"

        md += "---\n\n"

        # Research interests summary
        md += "## 🎯 Your Research Interests\n\n"
        for interest in self.research_interests:
            md += f"- {interest}\n"

        # Authors of interest
        if self.authors_of_interest:
            md += "\n## 👤 Authors of Interest\n\n"
            for author in self.authors_of_interest:
                md += f"- {author}\n"

        md += "\n---\n\n"

        # Group by day
        current_day = None
        conflict_section = []

        for talk, score in sorted_talks:
            day = talk.day or "Unknown Day"

            # New day section
            if day != current_day:
                current_day = day
                md += f"## 📅 {day}\n\n"

            # Check if this talk is in a conflict
            time_key = f"{talk.day}_{talk.time}" if talk.day and talk.time else None
            is_conflict = time_key in conflicts and len(conflicts[time_key]) > 1

            conflict_marker = "🔴 " if is_conflict else ""

            # Session type badge
            type_badge = "🎤 Talk" if talk.session_type == "talk" else "📋 Poster"

            # Talk entry
            md += f"### {conflict_marker}{talk.title}\n\n"
            md += f"**Type:** {type_badge} | **Relevance Score:** {score:.2%}\n\n"

            if talk.time:
                md += f"**⏰ Time:** {talk.time}\n\n"

            if talk.location:
                md += f"**📍 Location:** {talk.location}\n\n"

            if talk.session_name:
                md += f"**Session:** {talk.session_name}\n\n"

            if talk.authors:
                # Helper function for flexible author matching
                def matches_author_of_interest(author):
                    if not self.authors_of_interest:
                        return False
                    talk_tokens = [t.lower().strip('.,') for t in author.split() if len(t.strip('.,')) > 1]
                    for author_of_interest in self.authors_of_interest:
                        interest_tokens = [t.lower().strip('.,') for t in author_of_interest.split() if len(t.strip('.,')) > 1]
                        if all(token in talk_tokens for token in interest_tokens):
                            logger.info(f"✓ Author match: {author} matches {author_of_interest}")
                            return True
                    return False

                # Show ALL authors with highlighting for matches
                displayed_authors = []
                for author in talk.authors:
                    if matches_author_of_interest(author):
                        displayed_authors.append(f"**⭐ {author}**")  # Highlight with star
                    else:
                        displayed_authors.append(author)

                # Format: show all authors, with count
                md += f"**👥 Authors ({len(talk.authors)} total):** {', '.join(displayed_authors)}\n\n"

            md += f"**📝 Abstract:**\n\n{talk.abstract[:300]}"
            if len(talk.abstract) > 300:
                md += "..."
            md += "\n\n"

            # Add conflict info
            if is_conflict:
                conflict_talks = conflicts[time_key]
                md += f"⚠️ **CONFLICT:** {len(conflict_talks)} interesting talks at this time\n\n"
                conflict_section.append((time_key, conflict_talks))

            md += "---\n\n"

        # Conflicts summary at the end
        if conflict_section:
            md += "## 🔴 Scheduling Conflicts - Choose Wisely!\n\n"
            md += "These time slots have multiple relevant talks. You'll need to choose which to attend.\n\n"

            for time_key, conflict_talks in conflict_section:
                day, time = time_key.split('_', 1)
                md += f"### {day} at {time}\n\n"

                for talk, score in sorted(conflict_talks, key=lambda x: -x[1]):
                    type_emoji = "🎤" if talk.session_type == "talk" else "📋"
                    md += f"- {type_emoji} **{talk.title}** (Relevance: {score:.2%})\n"
                    md += f"  - Type: {'Talk' if talk.session_type == 'talk' else 'Poster'}\n"
                    md += f"  - Location: {talk.location or 'TBD'}\n"
                    md += f"  - Preview: {talk.abstract[:100]}...\n\n"

                md += "---\n\n"

        # Feedback section
        md += "## 📋 Notes & Feedback\n\n"
        md += "*Use this space to note your preferences for conflicting sessions:*\n\n"
        md += "<!-- Add your notes here -->\n\n"

        # Write to file
        with open(output_file, 'w') as f:
            f.write(md)

        logger.info(f"Generated schedule: {output_file}")
        print(f"\n✅ Schedule generated: {output_file}")
        print(f"   - {len(relevant_talks)} relevant talks")
        print(f"   - {len(conflicts)} conflicts detected")


# Example usage
async def main():
    """Example workflow"""

    # Initialize planner
    planner = ConferencePlanner(
        conference_name="ASHG2025",
        conference_dir="/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025"
    )

    # Parse conference PDF
    pdf_path = "/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025/ASHG-2025-Annual-Meeting-Abstracts.pdf"
    planner.parse_conference_pdf(pdf_path)

    # Get research interests
    planner.prompt_research_interests()

    # Save interests
    planner.save_research_interests("research_interests.md")

    # Index talks
    planner.index_talks()

    # Find relevant talks
    relevant_talks = planner.find_relevant_talks(top_k=50, min_relevance_score=0.3)

    # Generate schedule
    output_path = "/Users/camellia/PycharmProjects/PhD_Agent/conference/ASHG2025/ashg_schedule.md"
    planner.generate_schedule_markdown(relevant_talks, output_path)

    print("\n🎉 Conference planning complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
