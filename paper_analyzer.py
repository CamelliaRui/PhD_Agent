"""
Paper analysis and summarization module
"""

import asyncio
from typing import Dict, Any, List
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
import requests
from urllib.parse import urlparse
import PyPDF2
import io


class PaperAnalyzer:
    """Analyzes and summarizes academic papers using Claude Code SDK"""
    
    def __init__(self):
        self.setup_claude_client()
    
    def setup_claude_client(self):
        """Initialize Claude SDK client for paper analysis"""
        options = ClaudeCodeOptions(
            system_prompt="""You are an expert academic paper analyzer. Your role is to:
            1. Extract key information from research papers
            2. Provide comprehensive summaries
            3. Identify main contributions and novelty
            4. Analyze methodology and experimental design
            5. Evaluate results and conclusions
            6. Suggest connections to related work
            7. Identify potential improvements or extensions
            
            Always provide structured, scholarly analysis.""",
            allowed_tools=["WebFetch", "Read"],
            max_turns=5,
            permission_mode="acceptEdits"
        )
        
        self.client = ClaudeSDKClient(options=options)
    
    async def analyze_paper_from_url(self, paper_url: str) -> Dict[str, Any]:
        """
        Analyze a paper from a URL (arXiv, PDF link, etc.)
        
        Args:
            paper_url: URL to the paper
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Determine paper type and extract content
            paper_content = await self._extract_paper_content(paper_url)
            
            if not paper_content:
                return {"error": "Could not extract paper content"}
            
            # Analyze the paper content
            analysis = await self._analyze_content(paper_content, paper_url)
            return analysis
            
        except Exception as e:
            return {"error": f"Error analyzing paper: {str(e)}"}
    
    async def analyze_paper_text(self, paper_text: str, title: str = "") -> Dict[str, Any]:
        """
        Analyze paper from provided text content
        
        Args:
            paper_text: Full text of the paper
            title: Optional paper title
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            analysis = await self._analyze_content(paper_text, source=title)
            return analysis
            
        except Exception as e:
            return {"error": f"Error analyzing paper text: {str(e)}"}
    
    async def _extract_paper_content(self, url: str) -> str:
        """Extract paper content from URL"""
        try:
            parsed_url = urlparse(url)
            
            # Handle arXiv URLs
            if 'arxiv.org' in parsed_url.netloc:
                # Convert to PDF URL if needed
                if '/abs/' in url:
                    pdf_url = url.replace('/abs/', '/pdf/') + '.pdf'
                else:
                    pdf_url = url
                
                return await self._extract_pdf_content(pdf_url)
            
            # Handle direct PDF URLs
            elif url.endswith('.pdf'):
                return await self._extract_pdf_content(url)
            
            # Handle web pages
            else:
                async with self.client as client:
                    await client.query(f"Please extract the main content from this research paper URL: {url}")
                    
                    content = ""
                    async for message in client.receive_response():
                        if hasattr(message, 'content'):
                            for block in message.content:
                                if hasattr(block, 'text'):
                                    content += block.text
                    
                    return content
        
        except Exception as e:
            print(f"Error extracting paper content: {e}")
            return ""
    
    async def _extract_pdf_content(self, pdf_url: str) -> str:
        """Extract text content from PDF URL"""
        try:
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Read PDF content
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            return text_content
            
        except Exception as e:
            print(f"Error extracting PDF content: {e}")
            return ""
    
    async def _analyze_content(self, content: str, source: str = "") -> Dict[str, Any]:
        """Analyze paper content using Claude"""
        try:
            async with self.client as client:
                analysis_prompt = f"""
                Please provide a comprehensive analysis of this research paper:
                
                {content[:10000]}  # Limit content length
                
                Please structure your analysis as follows:
                
                1. **Paper Summary**
                   - Title and authors (if available)
                   - Main research question/problem
                   - Core hypothesis
                
                2. **Methodology**
                   - Research approach and methods used
                   - Experimental design
                   - Data sources and datasets
                   - Evaluation metrics
                
                3. **Key Findings**
                   - Main results and discoveries
                   - Statistical significance
                   - Performance metrics
                
                4. **Contributions**
                   - Novel contributions to the field
                   - Technical innovations
                   - Theoretical advances
                
                5. **Related Work**
                   - How this fits into existing literature
                   - Key references and comparisons
                   - Positioning relative to state-of-the-art
                
                6. **Limitations**
                   - Study limitations acknowledged by authors
                   - Potential weaknesses in methodology
                   - Scope constraints
                
                7. **Future Work**
                   - Authors' suggested future directions
                   - Potential extensions and improvements
                   - Open research questions
                
                8. **Critical Assessment**
                   - Strengths of the work
                   - Areas for improvement
                   - Significance to the field
                
                9. **Research Connections**
                   - How this relates to current trends
                   - Potential collaboration opportunities
                   - Applications in other domains
                """
                
                if source:
                    analysis_prompt += f"\n\nSource: {source}"
                
                await client.query(analysis_prompt)
                
                analysis_text = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                analysis_text += block.text
                
                # Parse structured analysis (this could be enhanced with proper parsing)
                return {
                    "source": source,
                    "analysis": analysis_text,
                    "timestamp": asyncio.get_event_loop().time()
                }
        
        except Exception as e:
            return {"error": f"Error in content analysis: {str(e)}"}
    
    async def compare_papers(self, papers: List[Dict[str, Any]]) -> str:
        """Compare multiple papers and identify relationships"""
        try:
            async with self.client as client:
                paper_summaries = []
                for i, paper in enumerate(papers, 1):
                    summary = f"Paper {i}: {paper.get('title', 'Unknown')}\n"
                    summary += f"Analysis: {paper.get('analysis', '')[:500]}...\n"
                    paper_summaries.append(summary)
                
                comparison_prompt = f"""
                Please compare and analyze the relationships between these research papers:
                
                {chr(10).join(paper_summaries)}
                
                Provide:
                1. Common themes and research areas
                2. Complementary findings
                3. Contradictions or disagreements
                4. Evolution of ideas across papers
                5. Potential synthesis opportunities
                6. Gaps that could be filled by future work
                """
                
                await client.query(comparison_prompt)
                
                comparison = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                comparison += block.text
                
                return comparison
        
        except Exception as e:
            return f"Error comparing papers: {str(e)}"
    
    async def generate_research_questions(self, paper_analysis: str, research_area: str = "") -> List[str]:
        """Generate research questions based on paper analysis"""
        try:
            async with self.client as client:
                prompt = f"""
                Based on this paper analysis:
                {paper_analysis}
                
                """
                
                if research_area:
                    prompt += f"And considering the research area: {research_area}\n"
                
                prompt += """
                Generate 10 specific, actionable research questions that could:
                1. Extend this work
                2. Address identified limitations
                3. Explore related problems
                4. Apply methods to new domains
                5. Challenge assumptions
                
                Format each question clearly and provide brief rationale.
                """
                
                await client.query(prompt)
                
                questions_text = ""
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                questions_text += block.text
                
                # Parse questions (simplified parsing)
                questions = [q.strip() for q in questions_text.split('\n') if q.strip() and ('?' in q or q.strip().startswith(('1.', '2.', '3.')))]
                return questions[:10]
        
        except Exception as e:
            return [f"Error generating questions: {str(e)}"]


# Example usage
async def main():
    analyzer = PaperAnalyzer()
    
    # Example arXiv paper
    arxiv_url = "https://arxiv.org/abs/2301.08727"
    analysis = await analyzer.analyze_paper_from_url(arxiv_url)
    
    print("Paper Analysis:")
    print(analysis.get('analysis', 'No analysis available'))


if __name__ == "__main__":
    asyncio.run(main())