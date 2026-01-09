"""
FastMCP Tools: YouTube Summary and PDF Q&A (Stateless Server)
Install dependencies:
pip install fastmcp youtube-transcript-api pypdf pinecone-client
"""

from fastmcp import FastMCP,Context
import pypdf
from pathlib import Path
import json
from mcp.shared.exceptions import UrlElicitationRequiredError
from mcp.types import ElicitRequestURLParams
# Add these imports at the top of server.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import sys,os
from services.pdf.pdf_ingestion import ingest_pdf_to_pinecone
from services.pdf import loader
from services.qa import _pdf_qa_simple, _pdf_qa_vector,_qa_from_web
from services.transcripts import extract_yt_transcript
from services.summarizer import get_yt_summary, get_pdf_summary
# 1. FORCE SILENCE: Redirect standard output to standard error
# This prevents libraries from printing text that breaks the JSON connection
# sys.stdout = sys.stderr
# --------------------------------------------------
# Initialize FastMCP server
# --------------------------------------------------
mcp = FastMCP("Analysis Tools")

# --------------------------------------------------
# YouTube Tools
# --------------------------------------------------

@mcp.tool()
def get_youtube_transcript(video_url: str) -> str:
    """
    Get the raw transcript of a YouTube video.
    
    Args:
        video_url: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)
    
    Returns:
        The complete video transcript as text
    """
    try:
        return extract_yt_transcript(video_url)
    except Exception as e:
        return f"Error getting transcript: {str(e)}"


@mcp.tool()
async def youtube_summary(video_url: str,ctx: Context, summary_style: str = "concise") -> str:
    """
    Summarize a YouTube video from its transcript.
    
    Args:
        video_url: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)
        summary_style: Style of summary - "concise" (default), "detailed", or "bullet_points"
    
    Returns:
        A summary of the video content
    """
    # Step 1: Notify user we are starting
    await ctx.report_progress(0.1, total=1.0, message="Fetching Transcript...")
    await ctx.info(f"Starting summary for {video_url} [{summary_style}]")
    try:
        transcript = extract_yt_transcript(video_url)
        return get_yt_summary(
            yt_transcript=transcript,
            level=summary_style
        )
    except Exception as e:
        return f"Error summarizing video: {str(e)}"

# --------------------------------------------------
# PDF Processing Tool (NO SERVER STATE)
# --------------------------------------------------

@mcp.tool()
async def process_pdf(pdf_path: str,ctx:Context) -> dict:
    """
    Smart PDF processor that checks page count and processes accordingly.
    - For PDFs with <= 2 pages: Saves content to .txt file
    - For PDFs with > 2 pages: Creates vector database
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        dict: Processing result with type, page_count, and relevant paths/info
    """
    try:
        reader = pypdf.PdfReader(pdf_path)
        page_count = len(reader.pages)
        pdf_file = Path(pdf_path)
        pdf_name = pdf_file.stem

        if page_count <= 2:
            await ctx.report_progress(0.5, message="Extracting text (Simple Mode)")
            content, status = loader.extract_text_from_pdf(pdf_path, "all")
            if not status:
                return {"error": "Failed to extract PDF content"}

            txt_path = pdf_file.with_suffix(".txt")
            txt_path.write_text(content, encoding="utf-8")
            # Notify client that a new file exists
            await ctx.session.send_resource_list_changed()
            await ctx.info(f"Created text file: {txt_path}")

            return {
                "status": "success",
                "processing_type": "simple",
                "pdf_path":pdf_path,
                "page_count": page_count,
                "txt_path": str(txt_path)
            }

        # Vector PDF
        # --- Strategy 2: Vector Ingestion ---
        await ctx.report_progress(progress=0.3, message="Starting Vector Ingestion (Pinecone)")
        await ctx.info("PDF > 2 pages. Switching to Vector Strategy.")
        result = await ingest_pdf_to_pinecone(pdf_path)
        await ctx.session.send_resource_list_changed()

        return {
            "status": "success",
            "processing_type": "vector",
            "pdf_path":pdf_path,
            "page_count": page_count,
            "namespace": result["namespace"],
            "chunk_count": result["chunks"]
        }

    except Exception as e:
        return {"error": f"Error processing PDF: {str(e)}"}

# --------------------------------------------------
# PDF Q&A Tool (CLIENT PROVIDES METADATA)
# --------------------------------------------------

@mcp.tool()
async def pdf_qa(pdf_info: dict,question: str,ctx:Context) -> str:
    """
    Smart Q&A tool that answers questions from a processed PDF.

    This tool automatically selects the correct Q&A strategy based on
    the PDF processing type provided by the client.

    Modes:
    - Simple PDFs:
        Uses full extracted text (from .txt or in-memory content)
        and sends it directly to the LLM.
    - Vector PDFs:
        Retrieves relevant chunks from the vector database (RAG)
        and generates an answer using those chunks.

    Args:
        pdf_info (dict):
            Metadata returned by `process_pdf`, must include:
            - processing_type: "simple" or "vector"
            - For simple PDFs:
                - txt_path OR content
            - For vector PDFs:
                - namespace
        question (str):
            Question to ask about the PDF content.

    Returns:
        str: Answer generated from the PDF content.
    """

    
    processing_type = pdf_info['processing_type']
    await ctx.debug(f"QA Request | Type: {processing_type} | Q: {question}")
    try:
        if processing_type == "simple":
            return _pdf_qa_simple(question, pdf_info)

        if processing_type == "vector":
            return _pdf_qa_vector(question, pdf_info)

        return "Error: Invalid processing type"

    except Exception as e:
        return f"Error answering question: {str(e)}"

# --------------------------------------------------
# PDF Text Extraction Tool
# --------------------------------------------------

@mcp.tool()
async def extract_pdf_text(pdf_path: str,ctx:Context,page_numbers: str = "all",summarization: bool = False) -> str:
    """
    Extract raw text from PDF pages or Extract text from a specific page of a PDF
    
    Args:
        pdf_path: Path to the PDF file
        page_numbers: Page numbers to extract (e.g., "1,3,5" or "all")
        summarization: Boolen (If user want summary of specific pages summarization = True else False)
    
    Returns:
        Extracted text content
    """
    await ctx.info(f"Extracting text from {pdf_path} (Pages: {page_numbers})")
    try:
        content, status = loader.extract_text_from_pdf(pdf_path, page_numbers)
        if not status:
            return "Error extracting text"

        if summarization:
            return get_pdf_summary(content)

        return content

    except Exception as e:
        return f"Error extracting text: {str(e)}"


@mcp.tool()
async def scrape_web_url(url: str,ctx:Context) -> dict:
    """
    Scrape content from a web URL and save it to a text file.
    
    Args:
        url: The web URL to scrape (e.g., https://example.com/article)
    
    Returns:
        dict: Contains status, url, txt_path, title, word_count, and timestamp
    """
    await ctx.info(f"Scraping URL: {url}")
    await ctx.report_progress(0.1, message="Connecting to website...")    
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"error": "Invalid URL format"}
        
        # Send request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        await ctx.report_progress(0.5, message="Parsing HTML...")

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = '\n'.join(lines)
        
        # Get title
        title = soup.title.string if soup.title else parsed.netloc
        
        # Generate filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"web_{safe_title}_{url_hash}.txt"
        
        # Save to file
        txt_path = Path(filename)
        txt_path.write_text(content, encoding='utf-8')

        await ctx.report_progress(1.0, message="Saved to file")
        await ctx.session.send_resource_list_changed()
        
        return {
            "status": "success",
            "url": url,
            "txt_path": str(txt_path),
            "title": title,
            "word_count": len(content.split()),
            "timestamp": datetime.now().isoformat(),
            "file_size_kb": round(len(content) / 1024, 2)
        }
        
    except requests.exceptions.Timeout:
        return {"error": "Request timeout - website took too long to respond"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection error - check your internet or the URL"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Error scraping URL: {str(e)}"}


@mcp.tool()
def web_content_qa(txt_path: str, query: str) -> str:
    """
    Answer questions about scraped web content from a text file.
    
    Args:
        txt_path: Path to the text file containing scraped content
        query: User's question about the web content
    
    Returns:
        str: Answer to the user's question based on the content
    """
    try:
        # Read the content
        file_path = Path(txt_path)
        if not file_path.exists():
            return f"Error: File not found at {txt_path}"
        
        content = file_path.read_text(encoding='utf-8')
        
        if not content.strip():
            return "Error: The text file is empty"
        
        return _qa_from_web(question=query,content=content)
        
    except Exception as e:
        return f"Error reading or processing file: {str(e)}"

# --------------------------------------------------
# Prompt Template (Reusable)
# --------------------------------------------------

@mcp.prompt()
def youtube_summarization_prompt(transcript: str, level: str = "concise"):
    """
    Prompt template for YouTube summarization.
    """
    return f"""
Summarize the following transcript at a **{level}** level.

Rules:
- Match the requested level.
- Preserve key ideas and intent.
- Avoid filler or repetition.
- Do not add new information.

Transcript:
{transcript}
"""

@mcp.resource("file://{filename}")
def get_file_content(filename: str) -> str:
    """Read a processed text file"""
    file_path = Path.cwd() / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return "Error: File not found."

# --------------------------------------------------
# Server Entry
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()

