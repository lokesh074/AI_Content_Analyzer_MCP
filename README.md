# AI Content Analyzer

An intelligent, multi-modal application that leverages the **Model Context Protocol (MCP)** and **Large Language Models (LLMs)** to analyze, summarize, and answer questions about PDFs, YouTube videos, and websites.

## 🌟 Features

-   **Multi-Modal Analysis**:
    -   **PDFs**: Automatic text extraction for small files and Vector RAG (Pinecone) for larger documents.
    -   **YouTube**: Extract transcripts and generate concise or detailed summaries.
    -   **Websites**: Scrape content on-the-fly for analysis and Q&A.
-   **Client-Server Architecture**: Built using the Model Context Protocol (MCP) to decouple the frontend (Streamlit) from the backend tools.
-   **Intelligent Routing**: The LLM automatically selects the best tool for the job based on your natural language query.
-   **Context-Aware Chat**: Switch between different active resources (Video, PDF, Web) to focus the AI's attention.

## Architecture

This project uses a split architecture to ensure modularity and scalability:

1.  **Frontend Client (`app.py`)**:
    -   Built with **Streamlit**.
    -   Acts as the MCP Host.
    -   Manages user session and resource uploads.
    -   Connects to the backend via standard input/output (stdio).

2.  **Backend Server (`server.py`)**:
    -   Built with **FastMCP**.
    -   Exposes specialized tools:
        -   `process_pdf`: Smart PDF ingestion.
        -   `pdf_qa`: RAG-based or simple Q&A.
        -   `get_youtube_transcript` & `youtube_summary`.
        -   `scrape_web_url`: Web scraper.

3.  **AI Engine**:
    -   **Groq API**: Powers the LLM for high-speed inference.
    -   **LangChain**: Orchestrates the interaction between the LLM and the MCP tools.

## 📂 Project Structure

```text
├── app.py                  # Main Streamlit Application (Client)
├── server.py               # FastMCP Server with Tool Definitions
├── client.py               # Standalone MCP Client (for testing/debugging)
├── services/               # Core Business Logic
│   ├── pdf/                # PDF Ingestion & Pinecone Logic
│   ├── transcripts/        # YouTube Transcript API Logic
│   ├── summarizer/         # Summarization prompts & logic
│   └── qa/                 # Q&A Logic (Simple & Vector)
├── requirements.txt        # Project Dependencies (if available)
└── .env                    # Environment Variables (API Keys)
```

## 🚀 Getting Started

### Prerequisites

-   **Python 3.10+**
-   **Groq API Key**: Get one at [console.groq.com](https://console.groq.com).
-   **Pinecone API Key**: Required for vector search features (Large PDFs).
-   **uv** (Optional but recommended): A fast Python package installer and resolver.

### Installation

1.  **Clone the Repository** (or download source):
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install Dependencies**:
    ```bash
    pip install streamlit langchain-groq langchain-mcp-adapters fastmcp pypdf youtube-transcript-api pinecone-client python-dotenv beautifulsoup4 requests
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```env
    GROQ_API_KEY=your_groq_api_key_here
    PINECONE_API_KEY=your_pinecone_api_key_here
    PINECONE_ENV=your_pinecone_environment (if needed)
    ```

4.  **Verify Paths**:
    Open `app.py` and ensure the paths for `UV_PATH`, `SERVER_SCRIPT`, and `PYTHON_PATH` match your local system configuration.
    > **Note**: This is critical for the Client-Server connection to work on Windows.

### ▶️ Running the Application

Run the Streamlit app:

```bash
streamlit run app.py
```

## 📖 Usage Guide

### 1. Adding Resources
Use the sidebar **"Resource Manager"** to add content:
-   **📄 PDF**: Upload a file. If it's >2 pages, it will be vectorized automatically.
-   **🎥 YouTube**: Paste a video URL to add it to the context.
-   **🌐 Website**: Enter a URL to scrape its text content.

### 2. Selecting Context
Select a resource under **"📝 Active Resource"** to focus the AI on that specific item. Select "🚫 None" for general chat.

### 3. Chatting
Ask questions naturally!
-   *"Summarize this video."*
-   *"What does page 3 of the PDF say?"*
-   *"What are the key takeaways from this website?"*

The AI will intelligently call the backend tools to fetch answers.

## 🛠️ Troubleshooting

-   **Connection Failed**: Check `app.py` line 26-28 to ensure the paths to `python.exe` and `server.py` are absolute and correct.
-   **Loop Errors (Windows)**: The code includes `asyncio.WindowsProactorEventLoopPolicy()` fixes, but ensure you are running Python 3.10+.

---
Developed for seamless multi-modal AI analysis.
