from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .pathway_pipeline import StreamingFeaturePipeline
from .rag_assistant import RagAssistant
from .risk_engine import DiseaseRiskEngine


class ChatRequest(BaseModel):
    question: str


class LiveState:
    def __init__(self) -> None:
        self.pipeline = StreamingFeaturePipeline(window_size=15)
        self.risk_engine = DiseaseRiskEngine()
        self.connections: set[WebSocket] = set()
        self.latest: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        self.alerts: list[dict[str, Any]] = []
        self.lock = asyncio.Lock()

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        for ws in stale:
            self.connections.discard(ws)


app = FastAPI(title="AgriGuardian AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

state = LiveState()
knowledge_dir = Path(__file__).resolve().parent / "knowledge"
assistant = RagAssistant(knowledge_dir=knowledge_dir)
reports_dir = Path(__file__).resolve().parent / "high_risk_reports"
reports_dir.mkdir(parents=True, exist_ok=True)


def persist_high_risk_report(payload: dict[str, Any]) -> str:
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


def generate_sensor_event() -> dict[str, Any]:
    crop = random.choice(["tomato", "rice", "wheat", "potato", "maize"])

    crop_ranges = {
        "tomato": (20, 34, 55, 92, 6.0, 7.0),
        "rice": (22, 35, 60, 95, 5.2, 6.8),
        "wheat": (15, 30, 40, 85, 6.2, 7.5),
        "potato": (16, 29, 50, 90, 5.0, 6.5),
        "maize": (18, 33, 45, 88, 5.8, 7.2),
    }

    t_min, t_max, h_min, h_max, ph_min, ph_max = crop_ranges[crop]
    temperature = random.uniform(t_min, t_max)
    humidity = random.uniform(h_min, h_max)
    rain_forecast = random.uniform(0, 1)
    wind_speed = random.uniform(0.5, 8)

    cloud_factor = 1 - rain_forecast * 0.55
    solar_radiation = random.uniform(120, 980) * cloud_factor
    soil_temperature = temperature - random.uniform(0.8, 3.5)
    leaf_wetness = min(
        100.0,
        max(
            5.0,
            humidity * 0.7 + rain_forecast * 25 + (2 - min(wind_speed, 2)) * 8,
        ),
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(temperature, 2),
        "humidity": round(humidity, 2),
        "rain_forecast": round(rain_forecast, 2),
        "soil_moisture": round(random.uniform(30, 85), 2),
        "wind_speed": round(wind_speed, 2),
        "leaf_wetness": round(leaf_wetness, 2),
        "soil_temperature": round(soil_temperature, 2),
        "soil_ph": round(random.uniform(ph_min, ph_max), 2),
        "solar_radiation": round(max(80.0, solar_radiation), 2),
        "crop_type": crop,
    }


async def simulator_loop() -> None:
    while True:
        event = generate_sensor_event()
        features = state.pipeline.process(event)
        risk = state.risk_engine.score(features.__dict__)

        payload = {
            **event,
            **features.__dict__,
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
        }

        alert_payload: dict[str, Any] | None = None
        if risk.alert_triggered:
            report_file = persist_high_risk_report(payload)
            alert_payload = {
                "timestamp": event["timestamp"],
                "message": f"High disease risk for {event['crop_type']} (score {risk.risk_score}).",
                "risk_level": risk.risk_level,
                "risk_score": risk.risk_score,
                "predicted_disease": risk.predicted_disease,
                "disease_confidence": risk.disease_confidence,
                "outbreak_eta_hours": risk.outbreak_eta_hours,
                "outbreak_window": risk.outbreak_window,
                "forecast_trajectory": risk.forecast_trajectory,
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

        await asyncio.sleep(2)


@app.on_event("startup")
async def on_startup() -> None:
    asyncio.create_task(simulator_loop())


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    async with state.lock:
        return {
            "latest": state.latest,
            "history": state.history[-60:],
            "alerts": state.alerts[-20:],
        }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    async with state.lock:
        live_context = dict(state.latest)

    result = assistant.answer(question=request.question, live_context=live_context)
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
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
    except Exception:
        state.connections.discard(websocket)


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
