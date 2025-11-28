"""
Database Layer for PhD Agent
Production-grade database management with ORM, migrations, and connection pooling
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.sql import func
import alembic
from alembic import command
from alembic.config import Config as AlembicConfig

Base = declarative_base()


# Database Models
class Paper(Base):
    """Paper entity"""
    __tablename__ = 'papers'

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, index=True)
    authors = Column(JSON)
    abstract = Column(Text)
    url = Column(String)
    source = Column(String)
    published_date = Column(DateTime)
    citations = Column(Integer, default=0)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    analyses = relationship("PaperAnalysis", back_populates="paper", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="paper", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_paper_title', 'title'),
        Index('idx_paper_published', 'published_date'),
    )


class PaperAnalysis(Base):
    """Paper analysis results"""
    __tablename__ = 'paper_analyses'

    id = Column(Integer, primary_key=True)
    paper_id = Column(String, ForeignKey('papers.id'))
    analysis_type = Column(String)  # summary, key_points, methodology, etc.
    content = Column(Text)
    quality_score = Column(Float)
    tokens_used = Column(Integer)
    model_version = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    paper = relationship("Paper", back_populates="analyses")


class CodebaseIndex(Base):
    """Indexed codebase information"""
    __tablename__ = 'codebase_indices'

    id = Column(Integer, primary_key=True)
    repository = Column(String, unique=True, index=True)
    github_url = Column(String)
    deepwiki_url = Column(String)
    paper_id = Column(String, ForeignKey('papers.id'), nullable=True)
    paper_title = Column(String)
    authors = Column(JSON)
    year = Column(Integer)
    pages_indexed = Column(Integer)
    has_readme = Column(Boolean)
    has_docs = Column(Boolean)
    index_data = Column(JSON)  # Stored index content
    indexed_at = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    paper = relationship("Paper", backref="codebase")
    queries = relationship("CodebaseQuery", back_populates="codebase", cascade="all, delete-orphan")


class CodebaseQuery(Base):
    """Codebase query history"""
    __tablename__ = 'codebase_queries'

    id = Column(Integer, primary_key=True)
    codebase_id = Column(Integer, ForeignKey('codebase_indices.id'))
    query_type = Column(String)  # ask, search
    query_text = Column(Text)
    response = Column(Text)
    latency_ms = Column(Float)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    codebase = relationship("CodebaseIndex", back_populates="queries")


class Discussion(Base):
    """Research discussions and brainstorming sessions"""
    __tablename__ = 'discussions'

    id = Column(Integer, primary_key=True)
    paper_id = Column(String, ForeignKey('papers.id'), nullable=True)
    topic = Column(String)
    context = Column(Text)
    user_message = Column(Text)
    agent_response = Column(Text)
    session_id = Column(String, index=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    paper = relationship("Paper", back_populates="discussions")


class MeetingAgenda(Base):
    """Generated meeting agendas"""
    __tablename__ = 'meeting_agendas'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    date = Column(DateTime)
    github_username = Column(String)
    content = Column(Text)
    github_activity = Column(JSON)
    papers_discussed = Column(JSON)
    action_items = Column(JSON)
    notion_page_id = Column(String)
    created_at = Column(DateTime, default=func.now())


class EvaluationRun(Base):
    """Evaluation run history"""
    __tablename__ = 'evaluation_runs'

    id = Column(Integer, primary_key=True)
    run_id = Column(String, unique=True, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    total_tasks = Column(Integer)
    successful_tasks = Column(Integer)
    failed_tasks = Column(Integer)
    success_rate = Column(Float)
    average_latency_ms = Column(Float)
    average_score = Column(Float)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    tasks = relationship("EvaluationTask", back_populates="run", cascade="all, delete-orphan")


class EvaluationTask(Base):
    """Individual evaluation task results"""
    __tablename__ = 'evaluation_tasks'

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('evaluation_runs.id'))
    task_id = Column(String)
    task_type = Column(String)
    success = Column(Boolean)
    score = Column(Float)
    latency_ms = Column(Float)
    error = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    run = relationship("EvaluationRun", back_populates="tasks")


class UserSession(Base):
    """User interaction sessions"""
    __tablename__ = 'user_sessions'

    id = Column(String, primary_key=True)
    user_id = Column(String)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    total_interactions = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    metadata = Column(JSON)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class PaperFeedback(Base):
    """User feedback on paper relevance and interest"""
    __tablename__ = 'paper_feedback'

    id = Column(Integer, primary_key=True)
    paper_id = Column(String, ForeignKey('papers.id'))
    user_id = Column(String, default='default_user')
    is_relevant = Column(Boolean, nullable=False)
    interest_level = Column(Integer)  # 1-5 scale
    read_status = Column(String)  # 'not_read', 'skimmed', 'read_fully'
    notes = Column(Text)
    tags = Column(JSON)  # User-defined tags
    feedback_date = Column(DateTime, default=func.now())
    source_context = Column(String)  # Where paper was found (journal_monitor, search, etc.)

    # Relationships
    paper = relationship("Paper", backref="feedback")

    __table_args__ = (
        Index('idx_feedback_user_paper', 'user_id', 'paper_id'),
        Index('idx_feedback_relevant', 'is_relevant'),
        Index('idx_feedback_date', 'feedback_date'),
    )


class UserResearchProfile(Base):
    """User's research interests and preferences learned from feedback"""
    __tablename__ = 'user_research_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, index=True, default='default_user')
    research_keywords = Column(JSON)  # List of keywords with weights
    preferred_sources = Column(JSON)  # Source preferences
    preferred_authors = Column(JSON)  # Frequently cited authors
    research_areas = Column(JSON)  # Research domains
    learning_data = Column(JSON)  # ML model data for relevance prediction
    total_papers_reviewed = Column(Integer, default=0)
    total_relevant_papers = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())


class DailyPaperDigest(Base):
    """Daily paper digest sent to user"""
    __tablename__ = 'daily_paper_digests'

    id = Column(Integer, primary_key=True)
    digest_date = Column(DateTime, default=func.now(), index=True)
    user_id = Column(String, default='default_user')
    papers_shown = Column(JSON)  # List of paper IDs shown
    papers_clicked = Column(JSON)  # List of paper IDs clicked
    papers_marked_relevant = Column(JSON)  # List of paper IDs marked relevant
    sources_searched = Column(JSON)  # Sources queried
    keywords_used = Column(JSON)  # Keywords used for search
    total_papers_found = Column(Integer)
    relevance_rate = Column(Float)  # Percentage of papers marked relevant
    metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())


# Database Manager
class DatabaseManager:
    """Manage database connections and operations"""

    def __init__(self, database_url: str, pool_size: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size

        # Create sync engine for migrations
        self.sync_engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            pool_pre_ping=True,
            echo=False
        )

        # Create async engine for operations
        async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
        self.async_engine = create_async_engine(
            async_url,
            pool_size=pool_size,
            pool_pre_ping=True,
            echo=False
        )

        # Session makers
        self.sync_session_factory = sessionmaker(bind=self.sync_engine)
        self.async_session_factory = async_sessionmaker(bind=self.async_engine)

    def init_db(self):
        """Initialize database tables"""
        Base.metadata.create_all(self.sync_engine)

    def run_migrations(self):
        """Run database migrations"""
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    @asynccontextmanager
    async def session(self) -> AsyncSession:
        """Get async database session"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def save_paper(self, paper_data: Dict[str, Any]) -> str:
        """Save a paper to the database"""
        async with self.session() as session:
            paper = Paper(
                id=paper_data.get('id', f"paper_{hash(paper_data['title'])}"),
                title=paper_data['title'],
                authors=paper_data.get('authors', []),
                abstract=paper_data.get('abstract'),
                url=paper_data.get('url'),
                source=paper_data.get('source'),
                published_date=paper_data.get('published_date'),
                citations=paper_data.get('citations', 0),
                metadata=paper_data.get('metadata', {})
            )
            session.add(paper)
            await session.flush()
            return paper.id

    async def save_analysis(self, paper_id: str, analysis_data: Dict[str, Any]) -> int:
        """Save paper analysis"""
        async with self.session() as session:
            analysis = PaperAnalysis(
                paper_id=paper_id,
                analysis_type=analysis_data['type'],
                content=analysis_data['content'],
                quality_score=analysis_data.get('quality_score'),
                tokens_used=analysis_data.get('tokens_used'),
                model_version=analysis_data.get('model_version'),
                metadata=analysis_data.get('metadata', {})
            )
            session.add(analysis)
            await session.flush()
            return analysis.id

    async def save_codebase_index(self, index_data: Dict[str, Any]) -> int:
        """Save indexed codebase"""
        async with self.session() as session:
            index = CodebaseIndex(
                repository=index_data['repository'],
                github_url=index_data['github_url'],
                deepwiki_url=index_data.get('deepwiki_url'),
                paper_id=index_data.get('paper_id'),
                paper_title=index_data.get('paper_title'),
                authors=index_data.get('authors', []),
                year=index_data.get('year'),
                pages_indexed=index_data.get('pages_indexed', 0),
                has_readme=index_data.get('has_readme', False),
                has_docs=index_data.get('has_docs', False),
                index_data=index_data.get('index_data', {})
            )
            session.add(index)
            await session.flush()
            return index.id

    async def get_paper_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Get paper by title"""
        async with self.session() as session:
            result = await session.execute(
                "SELECT * FROM papers WHERE title = :title",
                {"title": title}
            )
            row = result.fetchone()
            return dict(row) if row else None

    async def get_recent_papers(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently accessed papers"""
        async with self.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = await session.execute(
                """
                SELECT * FROM papers
                WHERE created_at >= :cutoff
                ORDER BY created_at DESC
                LIMIT :limit
                """,
                {"cutoff": cutoff_date, "limit": limit}
            )
            return [dict(row) for row in result.fetchall()]

    async def get_codebase_by_repo(self, repository: str) -> Optional[Dict[str, Any]]:
        """Get codebase index by repository"""
        async with self.session() as session:
            result = await session.execute(
                "SELECT * FROM codebase_indices WHERE repository = :repo",
                {"repo": repository}
            )
            row = result.fetchone()
            return dict(row) if row else None

    async def save_evaluation_run(self, metrics: Dict[str, Any], tasks: List[Dict[str, Any]]) -> str:
        """Save evaluation run results"""
        async with self.session() as session:
            run = EvaluationRun(
                run_id=f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_tasks=metrics['total_tasks'],
                successful_tasks=metrics['successful_tasks'],
                failed_tasks=metrics['failed_tasks'],
                success_rate=metrics['success_rate'],
                average_latency_ms=metrics['average_latency_ms'],
                average_score=metrics['average_score'],
                metrics=metrics
            )
            session.add(run)
            await session.flush()

            # Save individual tasks
            for task_data in tasks:
                task = EvaluationTask(
                    run_id=run.id,
                    task_id=task_data['task_id'],
                    task_type=task_data['task_type'],
                    success=task_data['success'],
                    score=task_data.get('score', 0.0),
                    latency_ms=task_data['latency_ms'],
                    error=task_data.get('error'),
                    metadata=task_data.get('metadata', {})
                )
                session.add(task)

            return run.run_id

    async def get_evaluation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get evaluation run history"""
        async with self.session() as session:
            result = await session.execute(
                """
                SELECT * FROM evaluation_runs
                ORDER BY created_at DESC
                LIMIT :limit
                """,
                {"limit": limit}
            )
            return [dict(row) for row in result.fetchall()]

    async def get_performance_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get performance statistics"""
        async with self.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get evaluation stats
            eval_result = await session.execute(
                """
                SELECT
                    COUNT(*) as total_runs,
                    AVG(success_rate) as avg_success_rate,
                    AVG(average_latency_ms) as avg_latency,
                    AVG(average_score) as avg_score
                FROM evaluation_runs
                WHERE created_at >= :cutoff
                """,
                {"cutoff": cutoff_date}
            )
            eval_stats = dict(eval_result.fetchone())

            # Get paper stats
            paper_result = await session.execute(
                """
                SELECT
                    COUNT(*) as papers_processed,
                    COUNT(DISTINCT source) as sources_used
                FROM papers
                WHERE created_at >= :cutoff
                """,
                {"cutoff": cutoff_date}
            )
            paper_stats = dict(paper_result.fetchone())

            # Get codebase stats
            codebase_result = await session.execute(
                """
                SELECT
                    COUNT(*) as repos_indexed,
                    SUM(pages_indexed) as total_pages
                FROM codebase_indices
                WHERE indexed_at >= :cutoff
                """,
                {"cutoff": cutoff_date}
            )
            codebase_stats = dict(codebase_result.fetchone())

            return {
                'evaluation': eval_stats,
                'papers': paper_stats,
                'codebases': codebase_stats
            }

    async def save_paper_feedback(
        self,
        paper_id: str,
        is_relevant: bool,
        interest_level: int = 3,
        read_status: str = 'not_read',
        notes: str = None,
        tags: List[str] = None,
        user_id: str = 'default_user',
        source_context: str = None
    ) -> int:
        """Save user feedback on a paper"""
        async with self.session() as session:
            feedback = PaperFeedback(
                paper_id=paper_id,
                user_id=user_id,
                is_relevant=is_relevant,
                interest_level=interest_level,
                read_status=read_status,
                notes=notes,
                tags=tags or [],
                source_context=source_context
            )
            session.add(feedback)
            await session.flush()
            return feedback.id

    async def get_user_feedback_history(
        self,
        user_id: str = 'default_user',
        days: int = 30,
        relevant_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's feedback history"""
        async with self.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)

            query = """
                SELECT pf.*, p.title, p.authors, p.abstract, p.source
                FROM paper_feedback pf
                JOIN papers p ON pf.paper_id = p.id
                WHERE pf.user_id = :user_id
                AND pf.feedback_date >= :cutoff
            """

            if relevant_only:
                query += " AND pf.is_relevant = TRUE"

            query += " ORDER BY pf.feedback_date DESC"

            result = await session.execute(
                query,
                {"user_id": user_id, "cutoff": cutoff_date}
            )
            return [dict(row) for row in result.fetchall()]

    async def update_research_profile(
        self,
        user_id: str = 'default_user'
    ) -> Dict[str, Any]:
        """Update user research profile based on feedback"""
        async with self.session() as session:
            # Get all relevant papers
            feedback_data = await self.get_user_feedback_history(
                user_id=user_id,
                days=90,
                relevant_only=True
            )

            if not feedback_data:
                return {'status': 'no_feedback', 'message': 'No feedback data available'}

            # Extract keywords from relevant papers
            from collections import Counter
            import re

            all_text = []
            all_authors = []
            all_sources = []

            for item in feedback_data:
                all_text.append(item.get('title', '') + ' ' + item.get('abstract', ''))
                all_authors.extend(item.get('authors', []))
                all_sources.append(item.get('source', ''))

            # Simple keyword extraction (words that appear frequently)
            text = ' '.join(all_text).lower()
            words = re.findall(r'\b[a-z]{4,}\b', text)
            word_counts = Counter(words)

            # Get top keywords
            top_keywords = dict(word_counts.most_common(50))

            # Author preferences
            author_counts = Counter(all_authors)
            top_authors = dict(author_counts.most_common(20))

            # Source preferences
            source_counts = Counter(all_sources)
            preferred_sources = dict(source_counts.most_common(10))

            # Check if profile exists
            profile_result = await session.execute(
                "SELECT * FROM user_research_profiles WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            existing_profile = profile_result.fetchone()

            total_reviewed = len(await self.get_user_feedback_history(user_id, days=90))
            total_relevant = len(feedback_data)

            if existing_profile:
                # Update existing profile
                await session.execute(
                    """
                    UPDATE user_research_profiles
                    SET research_keywords = :keywords,
                        preferred_sources = :sources,
                        preferred_authors = :authors,
                        total_papers_reviewed = :reviewed,
                        total_relevant_papers = :relevant,
                        last_updated = :now
                    WHERE user_id = :user_id
                    """,
                    {
                        "keywords": json.dumps(top_keywords),
                        "sources": json.dumps(preferred_sources),
                        "authors": json.dumps(top_authors),
                        "reviewed": total_reviewed,
                        "relevant": total_relevant,
                        "now": datetime.now(),
                        "user_id": user_id
                    }
                )
            else:
                # Create new profile
                profile = UserResearchProfile(
                    user_id=user_id,
                    research_keywords=top_keywords,
                    preferred_sources=preferred_sources,
                    preferred_authors=top_authors,
                    total_papers_reviewed=total_reviewed,
                    total_relevant_papers=total_relevant
                )
                session.add(profile)

            return {
                'status': 'success',
                'keywords': len(top_keywords),
                'authors': len(top_authors),
                'sources': len(preferred_sources),
                'total_reviewed': total_reviewed,
                'total_relevant': total_relevant,
                'relevance_rate': total_relevant / total_reviewed if total_reviewed > 0 else 0.0
            }

    async def get_research_profile(
        self,
        user_id: str = 'default_user'
    ) -> Optional[Dict[str, Any]]:
        """Get user's research profile"""
        async with self.session() as session:
            result = await session.execute(
                "SELECT * FROM user_research_profiles WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            row = result.fetchone()
            return dict(row) if row else None

    async def save_daily_digest(
        self,
        papers_shown: List[str],
        papers_clicked: List[str] = None,
        papers_marked_relevant: List[str] = None,
        sources_searched: List[str] = None,
        keywords_used: List[str] = None,
        total_papers_found: int = 0,
        user_id: str = 'default_user',
        metadata: Dict[str, Any] = None
    ) -> int:
        """Save daily paper digest record"""
        async with self.session() as session:
            relevance_rate = (
                len(papers_marked_relevant) / len(papers_shown)
                if papers_shown and papers_marked_relevant
                else 0.0
            )

            digest = DailyPaperDigest(
                user_id=user_id,
                papers_shown=papers_shown,
                papers_clicked=papers_clicked or [],
                papers_marked_relevant=papers_marked_relevant or [],
                sources_searched=sources_searched or [],
                keywords_used=keywords_used or [],
                total_papers_found=total_papers_found,
                relevance_rate=relevance_rate,
                metadata=metadata or {}
            )
            session.add(digest)
            await session.flush()
            return digest.id

    async def get_recent_digests(
        self,
        user_id: str = 'default_user',
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent daily digests"""
        async with self.session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = await session.execute(
                """
                SELECT * FROM daily_paper_digests
                WHERE user_id = :user_id
                AND digest_date >= :cutoff
                ORDER BY digest_date DESC
                """,
                {"user_id": user_id, "cutoff": cutoff_date}
            )
            return [dict(row) for row in result.fetchall()]


# Export database utilities
__all__ = [
    'DatabaseManager',
    'Paper',
    'PaperAnalysis',
    'CodebaseIndex',
    'CodebaseQuery',
    'Discussion',
    'MeetingAgenda',
    'EvaluationRun',
    'EvaluationTask',
    'UserSession',
    'PaperFeedback',
    'UserResearchProfile',
    'DailyPaperDigest',
    'Base'
]