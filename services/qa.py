from pinecone import Pinecone,ServerlessSpec
from pathlib import Path
import uuid,time
from prompts import QA_prompt
from utils import llm_call


MODEL_NAME = "llama-text-embed-v2"
BATCH_SIZE = 96
API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  
INDEX_NAME = "mcp-server"
DIMENSION = 1024

def _pdf_qa_vector(question: str, pdf_info: dict) -> str:
    """
    Internal function: Q&A for vector PDFs using RAG.
    Retrieves relevant chunks from Pinecone, concatenates them,
    and passes them to the LLM to generate an answer.
    """
    pc = Pinecone(api_key=API_KEY)
    # file_path = Path(pdf_path)
    # namespace = file_path.stem.replace(" ", "_")
    namespace = pdf_info['namespace']
    index = pc.Index(INDEX_NAME)

    try:
        # 1. Embed the query
        query_embedding = pc.inference.embed(
            model=MODEL_NAME,
            inputs=[question],
            parameters={"input_type": "query"}
        )

        # 2. Query vector DB
        results = index.query(
            namespace=namespace,
            vector=query_embedding[0]["values"],
            top_k=2,
            include_metadata=True
        )

        if not results.get("matches"):
            return "No relevant information found in the document."

        # 3. Concatenate retrieved chunks
        all_chunks = []
        for match in results["matches"]:
            meta = match.get("metadata", {})
            text = meta.get("text", "")
            if text:
                all_chunks.append(text)

        if not all_chunks:
            return "Retrieved chunks were empty."

        combined_context = "  ".join(all_chunks)

        # 4. Call LLM with combined context
        response = llm_call.llm_call(
            QA_prompt.format(
                content=combined_context,
                question=question
            )
        )

        return response

    except Exception as e:
        return f"Error in vector Q&A: {str(e)}"


from pathlib import Path


def _pdf_qa_simple(question: str, pdf_info: dict) -> str:
    """
    Internal function: Q&A for simple PDFs using full extracted text.
    """
    try:
        # Load content
        txt_path = pdf_info.get("txt_path")

        if txt_path and Path(txt_path).exists():
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = pdf_info.get("content", "")

        if not content.strip():
            return "No content available for this PDF."

        # Call LLM
        response = llm_call.llm_call(
            QA_prompt.format(
                content=content,
                question=question
            )
        )

        return response

    except Exception as e:
        return f"Error in simple Q&A: {str(e)}"

def _qa_from_web(question: str, content: str) -> str:
    """
    Internal function: Q&A for simple PDFs using full extracted text.
    """
    try:

        # Call LLM
        response = llm_call.llm_call(
            QA_prompt.format(
                content=content,
                question=question
            )[:7500]
        )

        return response

    except Exception as e:

        return f"Error in simple Q&A: {str(e)}"
