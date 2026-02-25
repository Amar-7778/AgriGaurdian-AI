from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RetrievedChunk:
    source: str
    content: str
    score: int


class RagAssistant:
    def __init__(self, knowledge_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> list[tuple[str, str]]:
        docs: list[tuple[str, str]] = []
        if not self.knowledge_dir.exists():
            return docs
        for file_path in sorted(self.knowledge_dir.glob("*.md")):
            docs.append((file_path.name, file_path.read_text(encoding="utf-8")))
        return docs

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z]{3,}", text.lower()))

    def retrieve(self, question: str, top_k: int = 3) -> list[RetrievedChunk]:
        q_tokens = self._tokens(question)
        ranked: list[RetrievedChunk] = []

        for source, content in self.knowledge:
            score = len(q_tokens.intersection(self._tokens(content)))
            ranked.append(RetrievedChunk(source=source, content=content[:1400], score=score))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    def answer(self, question: str, live_context: dict[str, Any]) -> dict[str, Any]:
        chunks = self.retrieve(question)
        context_blob = "\n\n".join(
            [f"Source: {c.source}\n{c.content}" for c in chunks if c.score > 0]
        )

        llm_response = self._try_llm(question=question, live_context=live_context, retrieved=context_blob)
        if llm_response:
            return {"answer": llm_response, "sources": [c.source for c in chunks if c.score > 0]}

        risk_level = live_context.get("risk_level", "UNKNOWN")
        risk_score = live_context.get("risk_score", "N/A")
        reasons = live_context.get("reasons", [])
        actions = live_context.get("suggested_actions", [])

        reasoning = " ".join(reasons[:3]) if reasons else "Risk is driven by current weather and crop conditions."
        action_text = " ".join(actions[:3]) if actions else "Continue monitoring and inspect canopy conditions."

        answer = (
            f"Current disease risk is {risk_level} (score: {risk_score}/100). "
            f"Why: {reasoning} "
            f"Recommended action: {action_text}"
        )
        return {"answer": answer, "sources": [c.source for c in chunks if c.score > 0]}

    def _try_llm(self, question: str, live_context: dict[str, Any], retrieved: str) -> str | None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = (
                "You are AgriGuardian AI, a crop disease early warning assistant. "
                "Use live telemetry and retrieved agriculture guidance. "
                "Be concise and practical.\n\n"
                f"Live context: {live_context}\n\n"
                f"Retrieved docs:\n{retrieved or 'No retrieved docs available.'}\n\n"
                f"Farmer question: {question}"
            )

            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You provide safe, evidence-grounded farm guidance."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception:
            return None
