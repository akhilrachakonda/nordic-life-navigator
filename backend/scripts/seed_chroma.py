"""
CLI script to seed ChromaDB with Swedish bureaucracy documents.

Usage:
    cd backend
    PYTHONPATH=$(pwd) python scripts/seed_chroma.py --data-dir data/

The script will:
1. Read all .md and .txt files from the data directory
2. Split them into chunks
3. Embed using text-embedding-004
4. Insert into ChromaDB
5. Optionally upload the resulting chroma_data/ to Firebase Storage
"""

import argparse
import hashlib
import logging
import os
import sys

import chromadb
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default chunk size and overlap
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def load_documents(data_dir: str) -> list[dict]:
    """Load .md and .txt files from a directory."""
    docs = []
    for filename in sorted(os.listdir(data_dir)):
        if filename.endswith((".md", ".txt")):
            filepath = os.path.join(data_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append({"filename": filename, "content": content})
            logger.info("Loaded %s (%d chars)", filename, len(content))
    return docs


def main():
    parser = argparse.ArgumentParser(description="Seed ChromaDB with bureaucracy docs")
    parser.add_argument("--data-dir", required=True, help="Directory with .md/.txt files")
    parser.add_argument("--chroma-dir", default="chroma_data", help="ChromaDB persist directory")
    parser.add_argument("--collection", default="bureaucracy_docs", help="Collection name")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY"), help="Gemini API key")
    args = parser.parse_args()

    if not args.api_key:
        logger.error("GEMINI_API_KEY not set. Pass --api-key or export env var.")
        sys.exit(1)

    genai.configure(api_key=args.api_key)

    # Load and chunk documents
    raw_docs = load_documents(args.data_dir)
    if not raw_docs:
        logger.error("No documents found in %s", args.data_dir)
        sys.exit(1)

    all_chunks = []
    all_metadatas = []
    all_ids = []

    for doc in raw_docs:
        chunks = split_text(doc["content"])
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.sha256(f"{doc['filename']}:{i}".encode()).hexdigest()[:16]
            all_chunks.append(chunk)
            all_metadatas.append({"source": doc["filename"], "chunk_index": i})
            all_ids.append(chunk_id)

    logger.info("Total chunks to embed: %d", len(all_chunks))

    # Embed all chunks
    embeddings = []
    for i, chunk in enumerate(all_chunks):
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=chunk,
            task_type="retrieval_document",
        )
        embeddings.append(result["embedding"])
        if (i + 1) % 50 == 0:
            logger.info("Embedded %d/%d chunks", i + 1, len(all_chunks))

    logger.info("All chunks embedded")

    # Insert into ChromaDB
    client = chromadb.PersistentClient(path=args.chroma_dir)
    collection = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"},
    )

    # Insert in batches of 100
    batch_size = 100
    for start in range(0, len(all_chunks), batch_size):
        end = min(start + batch_size, len(all_chunks))
        collection.add(
            documents=all_chunks[start:end],
            embeddings=embeddings[start:end],
            metadatas=all_metadatas[start:end],
            ids=all_ids[start:end],
        )
        logger.info("Inserted batch %d-%d", start, end)

    logger.info(
        "Seeding complete. Collection '%s' now has %d documents.",
        args.collection,
        collection.count(),
    )


if __name__ == "__main__":
    main()
