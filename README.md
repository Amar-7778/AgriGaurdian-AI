# AgriGuardian AI

AgriGuardian AI is a real-time agricultural early-warning system that estimates crop disease risk *before* visible symptoms appear by continuously processing live environmental signals and agronomic context.

## Key features

- **Live telemetry simulation** (for local/demo use):
  - Temperature
  - Humidity
  - Rain forecast
  - Soil moisture
  - Wind speed
  - Crop type
- **Streaming transformation pipeline (Pathway)**:
  - Rolling averages and smoothing over live signals
  - Threshold detection (e.g., humidity spikes)
  - Weather-condition feature extraction
  - Anomaly scoring for unusual environmental patterns
- **Disease risk engine**:
  - Risk score: **0–100**
  - Risk levels: **LOW / MEDIUM / HIGH**
- **Real-time alerting** when risk transitions to **HIGH**
- **RAG assistant** over local agriculture documents (optional LLM integration)
- **Live dashboard** with WebSocket updates, risk chart, alerts, and chat UI

## Why Pathway?

This project uses **Pathway** to model a *streaming-style* dataflow: telemetry events arrive continuously, are transformed into features (e.g., rolling aggregates), and then feed downstream logic such as the **risk engine** and **alerting**.

Pathway is used here to make the pipeline:
- **Incremental**: updates are processed as new events arrive (rather than recomputing everything)
- **Composable**: transformations can be added/removed as simple table operations
- **Suitable for real-time prototypes**: easy to demonstrate streaming feature extraction and derived signals

## Project structure

```text
backend/
  api.py
  pathway_pipeline.py
  rag_assistant.py
  risk_engine.py
  knowledge/
frontend/
  index.html
```

## Getting started (local)

### Prerequisites
- Python 3.10+ (recommended)
- pip

### 1) Create and activate a virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) (Optional) Configure LLM access
If you want the assistant to use an LLM, copy the example env file and set your key:

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`.

> If no API key is provided, AgriGuardian AI will still run using retrieval and rule-based responses.

### 4) Start the backend
```bash
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### 5) Open the dashboard
- http://localhost:8000

## API

- `GET /api/health` — Health check
- `GET /api/state` — Latest telemetry, history, and alerts
- `POST /api/chat` — RAG assistant Q&A
- `WS /ws` — Live telemetry and alert events

## Pathway pipeline

The Pathway-based streaming transformation pipeline is implemented in:

- `backend/pathway_pipeline.py`

It is responsible for converting raw telemetry events into higher-level signals used by the rest of the system, such as:
- Rolling averages (to reduce noise)
- Detected threshold events (e.g., sustained high humidity)
- Derived context features that influence disease risk
- Anomaly scores that can amplify risk under unusual conditions

### Run the Pathway example directly
```bash
python backend/pathway_pipeline.py
```

This runs a standalone, runnable example of the Pathway table transformations used for streaming-style feature extraction and alert-condition derivation.

## Demo (suggested flow)

1. Start the app and open the dashboard.
2. Observe sensor metrics updating every ~2 seconds.
3. Review the risk meter and real-time risk graph.
4. Wait for a **HIGH** risk condition to trigger alert cards.
5. Ask the assistant, for example:
   - “Why is disease risk high?”
   - “What preventive action should I take?”
   - “Is pesticide needed now?”

## Notes

- The runtime loop is event-driven, with continuous updates and WebSocket push to the UI.
- Risk logic is modular (`backend/risk_engine.py`) and can be replaced with an ML model.
- Pathway examples are isolated in `backend/pathway_pipeline.py`.
