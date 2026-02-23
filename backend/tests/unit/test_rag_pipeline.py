"""Unit tests for ai/rag_pipeline.py"""

from unittest.mock import MagicMock, patch

import pytest

from app.ai.rag_pipeline import RAGPipeline


@pytest.fixture
def mock_chroma():
    """Create a mock ChromaDB client with a fake collection."""
    client = MagicMock()
    collection = MagicMock()
    collection.query.return_value = {
        "documents": [["Skatteverket handles tax registration for all residents in Sweden."]],
        "metadatas": [[{"source": "skatteverket.md", "chunk_index": 0}]],
        "distances": [[0.15]],
    }
    client.get_or_create_collection.return_value = collection
    return client, collection


@pytest.fixture
def rag_pipeline(mock_chroma):
    client, _ = mock_chroma
    return RAGPipeline(
        chroma_client=client,
        collection_name="test_collection",
        embedding_model="text-embedding-004",
        top_k=3,
    )


@pytest.mark.asyncio
async def test_query_builds_augmented_prompt(rag_pipeline, mock_chroma):
    _, collection = mock_chroma

    with patch("app.ai.rag_pipeline.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

        result = await rag_pipeline.query(
            user_message="How do I get a personnummer?",
            chat_history=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ],
        )

    # Should contain the retrieved context
    assert "Skatteverket handles tax registration" in result
    # Should contain the user question
    assert "How do I get a personnummer?" in result
    # Should contain the chat history
    assert "Hi" in result
    assert "Hello! How can I help?" in result


@pytest.mark.asyncio
async def test_query_handles_empty_results(mock_chroma):
    client, collection = mock_chroma
    collection.query.return_value = {
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    pipeline = RAGPipeline(chroma_client=client, collection_name="test")

    with patch("app.ai.rag_pipeline.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}
        result = await pipeline.query("unknown topic", chat_history=[])

    assert "No relevant documentation found" in result


@pytest.mark.asyncio
async def test_query_handles_chroma_error():
    """If ChromaDB fails, the pipeline should degrade gracefully."""
    client = MagicMock()
    client.get_or_create_collection.side_effect = Exception("ChromaDB offline")
    pipeline = RAGPipeline(chroma_client=client, collection_name="test")

    with patch("app.ai.rag_pipeline.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}
        result = await pipeline.query("anything", chat_history=[])

    assert "retrieval error" in result.lower() or "No relevant documentation" in result


def test_format_chat_history_empty():
    result = RAGPipeline._format_chat_history([])
    assert result == "No previous conversation."


def test_format_chat_history_with_messages():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    result = RAGPipeline._format_chat_history(history)
    assert "User: Hello" in result
    assert "Assistant: Hi there!" in result
