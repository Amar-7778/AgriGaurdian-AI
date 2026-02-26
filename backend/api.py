"""FastAPI application with integrated Pathway ETL, RAG, and real-time streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import db
from .etl_pipeline import PathwayETLPipeline
from .rag_assistant import RagAssistant
from .risk_engine import DiseaseRiskEngine
from .streaming import FileStreamSource, HTTPStreamSource, KafkaStreamSource, StreamProcessor

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str


class LiveState:
    """Manages live state, connections, and data broadcasts."""

    def __init__(self) -> None:
        self.etl_pipeline = PathwayETLPipeline(window_size=15)
        self.risk_engine = DiseaseRiskEngine()
        self.connections: set[WebSocket] = set()
        self.latest: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        self.alerts: list[dict[str, Any]] = []
        self.lock = asyncio.Lock()
        self.stream_task: asyncio.Task[Any] | None = None
        self.stream_processor: StreamProcessor | None = None
        self.stream_source_type: str = "uninitialized"

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients."""
        stale: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        for ws in stale:
            self.connections.discard(ws)


# Initialize FastAPI app
app = FastAPI(title="AgriGuardian AI - Pathway ETL + RAG Pipeline")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize state and components
state = LiveState()
knowledge_dir = Path(__file__).resolve().parent / "knowledge"
assistant: RagAssistant | None = None
reports_dir = Path(__file__).resolve().parent / "high_risk_reports"
reports_dir.mkdir(parents=True, exist_ok=True)


def persist_high_risk_report(payload: dict[str, Any]) -> str:
    """Persist high-risk alerts to JSON files and database."""
    timestamp_value = str(payload.get("timestamp", datetime.now(timezone.utc).isoformat()))
    safe_timestamp = (
        timestamp_value.replace(":", "-")
        .replace("+", "_plus_")
        .replace(".", "_")
    )
    file_name = f"high_risk_{safe_timestamp}.json"
    file_path = reports_dir / file_name
    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return file_name


def _build_stream_source() -> tuple[str, KafkaStreamSource | HTTPStreamSource | FileStreamSource]:
    stream_source = os.getenv("STREAM_SOURCE", "kafka").strip().lower()

    if stream_source == "kafka":
        return (
            stream_source,
            KafkaStreamSource(
                bootstrap_servers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
                topic=os.getenv("KAFKA_TOPIC", "sensor-data"),
                group_id=os.getenv("KAFKA_GROUP_ID", "agriguardian-consumer"),
            ),
        )

    if stream_source == "http":
        return (
            stream_source,
            HTTPStreamSource(
                endpoint=os.getenv("HTTP_ENDPOINT", "http://localhost:8080/api/sensors"),
                poll_interval=int(os.getenv("HTTP_POLL_INTERVAL", "5")),
            ),
        )

    if stream_source == "file":
        return (
            stream_source,
            FileStreamSource(file_path=os.getenv("FILE_STREAM_PATH", "./sensor_data.jsonl")),
        )

    raise ValueError("Invalid STREAM_SOURCE. Use one of: kafka, http, file")


def _risk_payload(event: dict[str, Any], processed: dict[str, Any]) -> dict[str, Any]:
    risk = state.risk_engine.score(processed)
    timestamp = event.get("timestamp") or datetime.now(timezone.utc).isoformat()

    return {
        **event,
        **processed,
        "timestamp": timestamp,
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "reasons": risk.reasons,
        "suggested_actions": risk.suggested_actions,
        "predicted_disease": risk.predicted_disease,
        "disease_confidence": risk.disease_confidence,
        "disease_suggestions": risk.disease_suggestions,
        "outbreak_eta_hours": risk.outbreak_eta_hours,
        "outbreak_window": risk.outbreak_window,
        "forecast_trajectory": risk.forecast_trajectory,
        "action_plan": risk.action_plan,
        "ingestion_mode": state.stream_source_type,
    }


async def _handle_stream_event(message: dict[str, Any]) -> None:
    raw_event = message.get("raw", {})
    processed = message.get("processed")
    if not processed:
        return

    payload = _risk_payload(raw_event, processed)

    alert_payload: dict[str, Any] | None = None
    if payload["risk_level"] == "HIGH":
        report_file = persist_high_risk_report(payload)
        alert_payload = {
            "timestamp": payload["timestamp"],
            "message": f"🚨 HIGH RISK: {payload.get('crop_type', 'unknown')} - {payload['predicted_disease']}",
            "risk_level": payload["risk_level"],
            "risk_score": payload["risk_score"],
            "predicted_disease": payload["predicted_disease"],
            "disease_confidence": payload["disease_confidence"],
            "outbreak_eta_hours": payload["outbreak_eta_hours"],
            "outbreak_window": payload["outbreak_window"],
            "forecast_trajectory": payload["forecast_trajectory"],
            "report_file": report_file,
        }

    async with state.lock:
        state.latest = payload
        state.history.append(payload)
        if len(state.history) > 400:
            state.history = state.history[-400:]

        if alert_payload:
            state.alerts.append(alert_payload)
            if len(state.alerts) > 100:
                state.alerts = state.alerts[-100:]

    await state.broadcast({"type": "telemetry", "payload": payload})
    if alert_payload:
        await state.broadcast({"type": "alert", "payload": alert_payload})


async def _run_stream_processor() -> None:
    if state.stream_processor is None:
        return
    await state.stream_processor.start()


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database and start real-time stream processor."""
    logger.info("Initializing AgriGuardian AI...")

    db.init_sync()
    db.create_tables()
    logger.info("Database initialized")

    global assistant
    assistant = RagAssistant(knowledge_dir=knowledge_dir)
    logger.info("RAG assistant initialized")

    source_name, source = _build_stream_source()
    state.stream_source_type = source_name
    state.stream_processor = StreamProcessor(source=source, etl_pipeline=state.etl_pipeline)
    state.stream_processor.add_handler(_handle_stream_event)
    state.stream_task = asyncio.create_task(_run_stream_processor())
    logger.info("Real-time stream started with source: %s", source_name)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Gracefully stop stream processing."""
    if state.stream_processor:
        await state.stream_processor.stop()
    if state.stream_task and not state.stream_task.done():
        state.stream_task.cancel()
        try:
            await state.stream_task
        except asyncio.CancelledError:
            pass


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "AgriGuardian AI",
        "stream_source": state.stream_source_type,
        "stream_running": "true" if state.stream_task and not state.stream_task.done() else "false",
    }


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    """Get current live state including latest reading, history, and alerts."""
    async with state.lock:
        return {
            "latest": state.latest,
            "history": state.history[-60:],
            "alerts": state.alerts[-20:],
        }


@app.get("/api/pipeline/stats")
async def pipeline_stats() -> dict[str, Any]:
    """Get ETL pipeline statistics."""
    return state.etl_pipeline.get_statistics()


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    """Chat endpoint with RAG-enhanced responses."""
    if assistant is None:
        return {"answer": "RAG assistant not initialized yet.", "sources": []}

    async with state.lock:
        live_context = dict(state.latest)

    result = assistant.answer(question=request.question, live_context=live_context)
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    state.connections.add(websocket)
    try:
        async with state.lock:
            if state.latest:
                await websocket.send_json({"type": "telemetry", "payload": state.latest})
            for item in state.alerts[-5:]:
                await websocket.send_json({"type": "alert", "payload": item})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.connections.discard(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        state.connections.discard(websocket)


# Mount frontend
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
