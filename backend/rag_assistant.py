"""Legacy RAG Assistant - backward compatibility wrapper for VectorRAG."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .vector_rag import VectorRAG


class RagAssistant:
    """
    Legacy RagAssistant class maintained for backward compatibility.
    Delegates to the new VectorRAG system with vector embeddings.
    """

    def __init__(self, knowledge_dir: Path) -> None:
        """Initialize RAG with knowledge directory."""
        self.knowledge_dir = knowledge_dir
        self.vector_rag = VectorRAG(knowledge_dir=knowledge_dir)
        
        # Load and index documents on initialization
        indexed = self.vector_rag.load_and_index_documents()
        print(f"Indexed {indexed} chunks from knowledge base")

    def retrieve(self, question: str, top_k: int = 3):
        """Retrieve relevant chunks using vector similarity."""
        return self.vector_rag.retrieve(question, top_k=top_k)

    def answer(self, question: str, live_context: dict[str, Any]) -> dict[str, Any]:
        """Generate answer using RAG with live context."""
        return self.vector_rag.answer(question, live_context)
