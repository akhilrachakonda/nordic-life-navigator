"""Knowledge base ingestion script for Swedish public agency content."""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.ai.rag_pipeline import RAGPipeline
from app.core.config import settings
from app.core.dependencies import get_chroma_client

logger = logging.getLogger(__name__)

KNOWLEDGE_SOURCES = [
    {
        "url": "https://www.skatteverket.se/privat/folkbokforing/nyanlandisverige.4.3810a01c150939e893f26b0.html",
        "source": "skatteverket_registration",
        "agency": "Skatteverket",
    },
    {
        "url": "https://www.migrationsverket.se/English/Private-individuals/Studying-in-Sweden.html",
        "source": "migrationsverket_study",
        "agency": "Migrationsverket",
    },
    {
        "url": "https://www.csn.se/bidrag-och-lan/csn-in-english.html",
        "source": "csn_english",
        "agency": "CSN",
    },
    {
        "url": "https://www.forsakringskassan.se/english",
        "source": "forsakringskassan_english",
        "agency": "Försäkringskassan",
    },
    {
        "url": "https://www.1177.se/en/",
        "source": "1177_english",
        "agency": "1177 Vårdguiden",
    },
]

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def _extract_clean_text(html: str) -> str:
    """Remove noisy page sections and return compact body text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character chunks."""
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(text_len, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break
        start = max(0, end - overlap)

    return chunks


async def _ingest_source(
    client: httpx.AsyncClient,
    rag_pipeline: RAGPipeline,
    source_item: dict,
) -> tuple[int, int]:
    """Fetch, parse, chunk, and ingest one source. Returns (added, skipped)."""
    source_url = source_item["url"]
    source_name = source_item["source"]
    agency = source_item["agency"]

    try:
        response = await client.get(source_url)
        response.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch %s (%s): %s", source_name, source_url, e)
        return (0, 0)

    text = _extract_clean_text(response.text)
    chunks = _chunk_text(text)
    if not chunks:
        logger.warning("No ingestible text found for source %s", source_name)
        return (0, 0)

    ids = [f"{source_name}_{idx}" for idx in range(len(chunks))]
    collection = rag_pipeline._get_collection()
    existing = collection.get(ids=ids, include=[])
    existing_ids = set(existing.get("ids") or [])

    new_documents: list[str] = []
    new_metadatas: list[dict] = []
    new_ids: list[str] = []

    for idx, chunk in enumerate(chunks):
        chunk_id = f"{source_name}_{idx}"
        if chunk_id in existing_ids:
            continue

        new_ids.append(chunk_id)
        new_documents.append(chunk)
        new_metadatas.append(
            {
                "source": source_name,
                "agency": agency,
                "url": source_url,
                "chunk_index": idx,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    if new_ids:
        await rag_pipeline.add_documents(
            documents=new_documents,
            metadatas=new_metadatas,
            ids=new_ids,
        )

    skipped = len(chunks) - len(new_ids)
    logger.info(
        "Ingestion source=%s chunks_total=%d added=%d skipped_existing=%d",
        source_name,
        len(chunks),
        len(new_ids),
        skipped,
    )
    return (len(new_ids), skipped)


async def run_ingestion() -> dict:
    """Run ingestion across all configured knowledge sources."""
    rag_pipeline = RAGPipeline(
        chroma_client=get_chroma_client(),
        embedding_model=settings.EMBEDDING_MODEL,
    )

    total_added = 0
    total_skipped = 0

    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for source_item in KNOWLEDGE_SOURCES:
            added, skipped = await _ingest_source(client, rag_pipeline, source_item)
            total_added += added
            total_skipped += skipped

    summary = {
        "sources": len(KNOWLEDGE_SOURCES),
        "chunks_added": total_added,
        "chunks_skipped_existing": total_skipped,
    }
    logger.info("Ingestion summary: %s", summary)
    return summary


if __name__ == "__main__":
    asyncio.run(run_ingestion())
