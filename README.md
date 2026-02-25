# AgriGuardian AI

AgriGuardian AI is a real-time agricultural early warning system that predicts crop disease risk before visible symptoms by continuously processing live environmental data.

## What this starter includes

- Real-time event simulation for:
  - temperature
  - humidity
  - rain forecast
  - soil moisture
  - wind speed
  - crop type
- Streaming transformation pipeline with:
  - rolling averages
  - humidity threshold detection
  - weather condition analysis
  - anomaly scoring
- Disease risk engine with risk score (0-100) and levels (LOW/MEDIUM/HIGH)
- Real-time alerting when risk transitions to HIGH
- RAG assistant over local agriculture docs with optional LLM integration
- Live dashboard with WebSocket updates, risk graph, alerts, and chat UI

## Project structure

```text
/backend
  api.py
  pathway_pipeline.py
  risk_engine.py
  rag_assistant.py
  /knowledge
/frontend
  index.html
```

## Run locally

1. Create and activate Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional LLM setup:

- Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
- If no key is set, AgriGuardian still works with retrieval + rule-based responses.

4. Start backend:

```bash
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

5. Open dashboard:

- http://localhost:8000

## API endpoints

- `GET /api/health` - health check
- `GET /api/state` - latest telemetry + history + alerts
- `POST /api/chat` - RAG assistant question answering
- `WS /ws` - live telemetry and alert events

## Pathway streaming pipeline example

A runnable Pathway table transformation example is included in:

- `backend/pathway_pipeline.py`

Run it directly:

```bash
python backend/pathway_pipeline.py
```

It demonstrates Pathway table usage for streaming-style feature extraction and alert condition derivation.

## Demo flow for hackathon

1. Start app and open dashboard.
2. Watch live sensor metrics update every 2 seconds.
3. Observe risk meter and real-time graph.
4. Wait for HIGH risk condition to trigger alert cards.
5. Ask assistant:
   - "Why is disease risk high?"
   - "What preventive action should I take?"
   - "Is pesticide needed now?"

## Notes

- The runtime event loop is event-driven with continuous updates and instant WebSocket push.
- Risk logic is modular in `backend/risk_engine.py` and easy to replace with ML models.
- Pathway examples are isolated in `backend/pathway_pipeline.py` for fast extension to real connectors (Kafka/CSV).
