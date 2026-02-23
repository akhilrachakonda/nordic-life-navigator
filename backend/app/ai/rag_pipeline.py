"""
RAG Pipeline — retrieval-augmented generation using ChromaDB + Gemini embeddings.

Responsibilities:
- Embed user queries via text-embedding-004
- Retrieve top-k relevant chunks from ChromaDB
- Construct augmented prompts with retrieved context and chat history
- Manage document ingestion
"""

import logging
from typing import Optional

import chromadb
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

BUREAUCRACY_SYSTEM_INSTRUCTION = """You are Nordic Life Navigator, an AI assistant \
specialized in helping international students and migrants navigate Swedish bureaucracy.

You help with:
- Skatteverket (Swedish Tax Agency) — tax registration, personal numbers
- Migrationsverket (Migration Agency) — residence permits, visa extensions
- CSN (Student Finance) — student loans and grants
- Försäkringskassan (Social Insurance) — social benefits
- Other Swedish government services

Rules:
1. Always cite your sources when referencing specific regulations or procedures.
2. If you are unsure, say so explicitly — never fabricate procedures.
3. Be empathetic. Many users are stressed navigating a foreign bureaucracy.
4. Provide step-by-step guidance when possible.
5. If the user's question is outside Swedish bureaucracy, politely redirect.
"""

RAG_PROMPT_TEMPLATE = """Use the following context retrieved from official Swedish \
bureaucracy documentation to answer the user's question. If the context does not \
contain enough information, say so honestly.

--- RETRIEVED CONTEXT ---
{context}
--- END CONTEXT ---

--- CONVERSATION HISTORY ---
{chat_history}
--- END HISTORY ---

User question: {question}

Provide a clear, helpful answer:"""


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline backed by ChromaDB."""

    def __init__(
        self,
        chroma_client: chromadb.ClientAPI,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
        embedding_model: str = settings.EMBEDDING_MODEL,
        top_k: int = settings.RAG_TOP_K,
    ):
        self._chroma_client = chroma_client
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._top_k = top_k
        self._collection: Optional[chromadb.Collection] = None

    def _get_collection(self) -> chromadb.Collection:
        """Lazy-load the ChromaDB collection."""
        if self._collection is None:
            try:
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                logger.error("Failed to access ChromaDB collection: %s", e)
                raise
        return self._collection

    async def query(
        self, user_message: str, chat_history: list[dict]
    ) -> str:
        """
        Build an augmented prompt by retrieving relevant context from ChromaDB.

        Args:
            user_message: The current user question.
            chat_history: List of dicts with 'role' and 'content' keys.

        Returns:
            A fully constructed prompt with retrieved context + history.
        """
        context = await self._retrieve_context(user_message)
        history_str = self._format_chat_history(chat_history)

        return RAG_PROMPT_TEMPLATE.format(
            context=context,
            chat_history=history_str,
            question=user_message,
        )

    async def _retrieve_context(self, query_text: str) -> str:
        """Embed the query and retrieve top-k documents from ChromaDB."""
        try:
            collection = self._get_collection()

            # Embed the query using Gemini embedding model
            embedding_result = genai.embed_content(
                model=f"models/{self._embedding_model}",
                content=query_text,
                task_type="retrieval_query",
            )
            query_embedding = embedding_result["embedding"]

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=self._top_k,
            )

            if not results["documents"] or not results["documents"][0]:
                logger.info("No relevant documents found for query")
                return "No relevant documentation found."

            # Format retrieved chunks with source metadata
            chunks = []
            for i, (doc, meta) in enumerate(
                zip(results["documents"][0], results["metadatas"][0])
            ):
                source = meta.get("source", "unknown")
                chunks.append(f"[Source: {source}]\n{doc}")

            return "\n\n".join(chunks)

        except Exception as e:
            logger.warning("ChromaDB retrieval failed, proceeding without context: %s", e)
            return "No relevant documentation found (retrieval error)."

    @staticmethod
    def _format_chat_history(chat_history: list[dict]) -> str:
        """Format chat history into a readable string for the prompt."""
        if not chat_history:
            return "No previous conversation."

        lines = []
        for msg in chat_history:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        """Add documents to the ChromaDB collection with embeddings."""
        collection = self._get_collection()

        # Batch embed all documents
        embeddings = []
        for doc in documents:
            result = genai.embed_content(
                model=f"models/{self._embedding_model}",
                content=doc,
                task_type="retrieval_document",
            )
            embeddings.append(result["embedding"])

        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info("Added %d documents to ChromaDB collection", len(documents))
