from pinecone import Pinecone,ServerlessSpec
from pathlib import Path
import uuid,time
from services.pdf.chunker import chunk_text
from services.pdf.loader import extract_text_from_pdf

MODEL_NAME = "llama-text-embed-v2"
BATCH_SIZE = 96
API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  
INDEX_NAME = "mcp-server"
DIMENSION = 1024

async def ingest_pdf_to_pinecone(pdf_path: str):
    pc = Pinecone(api_key=API_KEY)

    # Check if index exists, if not create it

    existing_indexes = pc.list_indexes().names()
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        # Wait for index to be initialized
        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(1)
        print("Index created successfully.")
    else:
        print(f"Index '{INDEX_NAME}' already exists.")

    pdf_file = Path(pdf_path)
    print("pdf_file : ",pdf_file.name)

    if not pdf_file.exists():
        raise FileNotFoundError("PDF not found")

    namespace = pdf_file.stem.replace(" ", "_")
    index = pc.Index(INDEX_NAME)
    text,status = extract_text_from_pdf(pdf_path)
    # text = extract_text_from_pdf(pdf_path)

    chunks = chunk_text(text)

    records = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        records.append({
            "id": f"{namespace}_{uuid.uuid4()}",
            "text": chunk,
            "metadata": {
                "pdf_name": pdf_file.name,
                "chunk_index": i,
                "text": chunk
            }
        })

        if len(records) >= BATCH_SIZE:
            _embed_and_upsert(records, pc, index, namespace)
            records = []

    if records:
        _embed_and_upsert(records, pc, index, namespace)

    return {
        "namespace": namespace,
        "chunks": len(chunks)
    }


def _embed_and_upsert(records, pc, index, namespace):
    texts = [r["text"] for r in records]

    embeddings = pc.inference.embed(
        model=MODEL_NAME,
        inputs=texts,
        parameters={"input_type": "passage"}
    )

    vectors = [
        {
            "id": r["id"],
            "values": embeddings[i]["values"],
            "metadata": r["metadata"]
        }
        for i, r in enumerate(records)
    ]

    index.upsert(vectors=vectors, namespace=namespace)


