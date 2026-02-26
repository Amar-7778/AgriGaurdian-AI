"""Enhanced RAG system with vector embeddings and semantic search."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from .db import RAGChunk, RAGDocument, DatabaseManager, db

# Initialize embedding model (lightweight + fast)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim, 22MB, suitable for CPU


@dataclass
class RetrievedChunk:
    """Retrieved document chunk with metadata."""
    document_id: int
    filename: str
    text: str
    similarity_score: float


class VectorRAG:
    """Vector-based RAG system with semantic search using embeddings."""

    def __init__(self, knowledge_dir: Path | None = None, db_manager: DatabaseManager = db):
        self.knowledge_dir = knowledge_dir or Path(__file__).resolve().parent / "knowledge"
        self.db_manager = db_manager
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self.chunk_size = 300
        self.chunk_overlap = 50

    def load_and_index_documents(self) -> int:
        """
        Load markdown documents and index them with embeddings.
        Returns the number of chunks indexed.
        """
        if not self.knowledge_dir.exists():
            return 0

        session = self.db_manager.get_session()
        indexed_count = 0

        try:
            for file_path in sorted(self.knowledge_dir.glob("*.md")):
                content = file_path.read_text(encoding="utf-8")
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                # Check if document already exists
                existing = session.query(RAGDocument).filter_by(content_hash=content_hash).first()
                if existing:
                    continue

                # Create document record
                doc = RAGDocument(
                    filename=file_path.name,
                    content=content,
                    content_hash=content_hash
                )
                session.add(doc)
                session.flush()

                # Split into chunks
                chunks = self._split_text(content)
                for chunk_idx, chunk_text in enumerate(chunks):
                    embedding = self.embedder.encode(chunk_text)
                    embedding_json = json.dumps(embedding.tolist())

                    chunk_record = RAGChunk(
                        document_id=doc.id,
                        chunk_index=chunk_idx,
                        text=chunk_text,
                        vector=embedding_json,
                        embedding_model=EMBEDDING_MODEL
                    )
                    session.add(chunk_record)
                    indexed_count += 1

            session.commit()
        finally:
            session.close()

        return indexed_count

    def retrieve(self, question: str, top_k: int = 3) -> list[RetrievedChunk]:
        """
        Retrieve most relevant chunks using vector similarity search.
        """
        session = self.db_manager.get_session()

        try:
            # Encode question
            question_embedding = self.embedder.encode(question)

            # Get all chunks with embeddings
            chunks = session.query(RAGChunk, RAGDocument).join(
                RAGDocument, RAGChunk.document_id == RAGDocument.id
            ).all()

            if not chunks:
                return []

            # Calculate similarity scores
            scored_chunks = []
            for chunk, doc in chunks:
                chunk_embedding = np.array(json.loads(chunk.vector))
                similarity = float(np.dot(question_embedding, chunk_embedding) / (
                    np.linalg.norm(question_embedding) * np.linalg.norm(chunk_embedding) + 1e-8
                ))
                scored_chunks.append((chunk, doc, similarity))

            # Sort by similarity and return top-k
            scored_chunks.sort(key=lambda x: x[2], reverse=True)

            retrieved = []
            for chunk, doc, score in scored_chunks[:top_k]:
                if score > 0.1:  # Minimum similarity threshold
                    retrieved.append(RetrievedChunk(
                        document_id=doc.id,
                        filename=doc.filename,
                        text=chunk.text[:1500],
                        similarity_score=round(score, 3)
                    ))

            return retrieved

        finally:
            session.close()

    def answer(self, question: str, live_context: dict[str, Any]) -> dict[str, Any]:
        """
        Generate answer using RAG with live context.
        Falls back to rule-based response if LLM unavailable.
        """
        chunks = self.retrieve(question)
        context_blob = "\n\n".join([
            f"[Source: {c.filename}, Relevance: {c.similarity_score}]\n{c.text}"
            for c in chunks
        ])

        # Try LLM first
        llm_response = self._try_llm(
            question=question,
            live_context=live_context,
            retrieved=context_blob
        )

        if llm_response:
            return {
                "answer": llm_response,
                "sources": [c.filename for c in chunks],
                "confidence": "high",
                "method": "llm"
            }

        # Fall back to rule-based answer
        risk_level = live_context.get("risk_level", "UNKNOWN")
        risk_score = live_context.get("risk_score", "N/A")
        reasons = live_context.get("reasons", [])
        actions = live_context.get("suggested_actions", [])
        crop = live_context.get("crop_type", "crop")

        reasoning = " ".join(reasons[:2]) if reasons else "Risk influenced by current environmental conditions."
        action_text = " ".join(actions[:2]) if actions else "Continue monitoring and inspect canopy closely."

        answer = (
            f"For your {crop}: Disease risk is **{risk_level}** (score: {risk_score}/100). "
            f"\n\nWhy: {reasoning} "
            f"\n\nAction: {action_text}"
        )

        return {
            "answer": answer,
            "sources": [c.filename for c in chunks],
            "confidence": "medium",
            "method": "rule-based"
        }

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks with overlap."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence.split())
            if current_length + sentence_length > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    # Keep overlap: last ~50% of previous chunk
                    current_chunk = current_chunk[-len(current_chunk) // 2:]
                    current_length = sum(len(s.split()) for s in current_chunk)

            current_chunk.append(sentence)
            current_length += sentence_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _try_llm(self, question: str, live_context: dict[str, Any], retrieved: str) -> str | None:
        """Attempt to get response from OpenAI LLM."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = (
                "You are AgriGuardian AI, an expert crop disease prediction assistant. "
                "Use the retrieved agricultural knowledge and live telemetry data. "
                "Provide concise, actionable recommendations.\n\n"
                f"Live context: {json.dumps(live_context, indent=2)}\n\n"
                f"Retrieved knowledge:\n{retrieved or 'No retrieved documents.'}\n\n"
                f"Farmer question: {question}"
            )

            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "Provide safe, evidence-based agricultural guidance grounded in agronomy."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM error: {e}")
            return None
