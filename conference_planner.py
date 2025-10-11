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
        
        ASHG format pattern:
        - Title: Lines before "Subsession Time:" 
        - Time: "Subsession Time: Day, Month Date at Time"
        - Authors: "Authors: Name1 (Affiliation1), Name2 (Affiliation2), ..."
        - Abstract: "Abstract: Content..."
        """
        talks = []
        
        # Split by looking for title patterns followed by Subsession Time
        # The title usually appears 1-2 lines before "Subsession Time:"
        sections = []
        
        # Find all "Subsession Time:" positions and extract surrounding context
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'Subsession Time:' in line:
                # Look backwards for the title (usually 1-3 lines before)
                title_lines = []
                for j in range(max(0, i-5), i):
                    prev_line = lines[j].strip()
                    if (prev_line and 
                        not prev_line.startswith(('ASHG', 'indicates', 'Session', 'Location:', 'Time:')) and
                        len(prev_line) > 20 and
                        not ('(' in prev_line and ')' in prev_line and 
                             any(inst in prev_line.lower() for inst in ['university', 'institute', 'hospital', 'center']))):
                        title_lines.append(prev_line)
                
                # Take the last (closest) title line
                title = title_lines[-1] if title_lines else None
                
                # Extract the section from this point forward until next subsection or end
                section_lines = [line]  # Include the Subsession Time line
                for k in range(i+1, len(lines)):
                    if 'Subsession Time:' in lines[k]:
                        break
                    section_lines.append(lines[k])
                
                if title:
                    section_text = '\n'.join([title] + section_lines)
                    sections.append(section_text)
        
        # Parse each section
        for section in sections:
            try:
                talk = self._parse_single_ashg_abstract_v2(section)
                if talk:
                    talks.append(talk)
            except Exception as e:
                logger.debug(f"Failed to parse section: {e}")
                continue
        
        logger.info(f"ASHG parser extracted {len(talks)} talks")
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
        authors_line = None
        abstract_text = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Extract timing information
            if 'Subsession Time:' in line:
                day_time_match = re.search(r'(\w+, \w+ \d+) at ([\d:apm –-]+)', line)
                day = day_time_match.group(1) if day_time_match else None
                time = day_time_match.group(2) if day_time_match else None
                continue
            
            # Look for authors line
            if line.startswith('Authors:'):
                authors_line = line[8:].strip()  # Remove "Authors:" prefix
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
                session_type="talk",  # ASHG abstracts are typically talks
                day=day,
                time=time
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
        
        # Find title, authors, and abstract
        title = None
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
                time=time
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

            self.research_interests = interests
            self.exclusion_topics = exclusions
            logger.info(f"Loaded {len(interests)} interests and {len(exclusions)} exclusions")
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
                        return existing_interests
                    elif choice == 'r':
                        print("\n🔄 Starting fresh...\n")
                        interests = []
                    else:  # default to 'add'
                        print(f"\n➕ Adding to existing interests...\n")
                        # Filter out NA entries
                        interests = [i for i in existing_interests if i.strip() and i.strip().upper() != 'NA']
                else:
                    interests = []
            except Exception as e:
                logger.debug(f"Could not load existing interests: {e}")
                interests = []
        else:
            interests = []

        # Show instructions
        if not interests:
            print("\nPlease describe your research interests for conference planning.")
            print("This will help match talks and posters relevant to your work.")
            print("\n💡 Examples:")
            print("  - CRISPR gene editing and therapeutic applications")
            print("  - Population genetics and evolutionary biology")
            print("  - Cancer genomics and precision medicine")
            print("  - Machine learning for genomic prediction")
            print("  - Statistical fine-mapping for genetic data")
            print("  - eQTLs, QTLs, and regulatory elements")
        else:
            print("\n💡 Add more interests to complement the ones above.")

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

        return interests

    def save_research_interests(self, output_file: str):
        """Save research interests and exclusion topics to markdown file"""
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

        with open(output_file, 'w') as f:
            f.write(content)

        logger.info(f"Saved research interests to {output_file}")
        print(f"💾 Research interests saved to: {output_file}")

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

        for talk in self.talks:
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
            ids.append(talk.presentation_id)

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

        # Combine all research interests into query
        query_text = " ".join(self.research_interests)

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

                # Apply exclusion filter
                if not self.should_exclude_talk(talk):
                    relevant_talks.append((talk, similarity))
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

            # Talk entry
            md += f"### {conflict_marker}{talk.title}\n\n"
            md += f"**Relevance Score:** {score:.2%}\n\n"

            if talk.time:
                md += f"**⏰ Time:** {talk.time}\n\n"

            if talk.location:
                md += f"**📍 Location:** {talk.location}\n\n"

            if talk.session_name:
                md += f"**Session:** {talk.session_name}\n\n"

            if talk.authors:
                md += f"**👥 Authors:** {', '.join(talk.authors[:3])}"
                if len(talk.authors) > 3:
                    md += f" *et al.* ({len(talk.authors)} total)"
                md += "\n\n"

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
                    md += f"- **{talk.title}** (Relevance: {score:.2%})\n"
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
