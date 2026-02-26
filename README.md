# AgriGuardian AI - Pathway ETL + Vector RAG Pipeline

<<<<<<< HEAD
**Production-Ready Agricultural Disease Prediction System** with real-time data processing, vector-based semantic search, and scalable streaming architecture.

This runtime no longer generates synthetic telemetry internally. Data ingestion is external-source driven via Kafka, HTTP polling, or file stream connectors.

## 🚀 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                                  │
│  (Kafka | HTTP APIs | Sensors | Files)                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              STREAMING LAYER (streaming.py)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Kafka      │  │   HTTP       │  │   Files      │           │
│  │ Consumer     │  │   Polling    │  │   Streaming  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│          PATHWAY ETL PIPELINE (etl_pipeline.py)                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  • Raw Data Ingestion                                │       │
│  │  • Feature Engineering (rolling windows, anomalies)  │       │
│  │  • Data Enrichment & Validation                      │       │
│  │  • Real-time Stream Processing                       │       │
│  └──────────────────────────────────────────────────────┘       │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│  RISK ENGINE         │  │  DATABASE PERSIST    │
│  (risk_engine.py)    │  │  (sensor_readings,   │
│                      │  │   features, risks)   │
│  Disease Prediction  │  │                      │
│  Risk Scoring        │  │  SQLAlchemy ORM      │
│  Alert Generation    │  │  PostgreSQL/SQLite   │
└──────────┬───────────┘  └──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│         VECTOR RAG SYSTEM (vector_rag.py)                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  • Document Embedding (all-MiniLM-L6-v2)            │       │
│  │  • Vector Similarity Search (cosine distance)        │       │
│  │  • Semantic Chunking (300 chars, 50 char overlap)    │       │
│  │  • Dynamic LLM Integration (GPT-4o-mini)             │       │
│  │  • Fallback Rule-Based Responses                     │       │
│  └──────────────────────────────────────────────────────┘       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           FASTAPI SERVER (api.py)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  /api/chat   │  │  /api/state  │  │  /ws         │           │
│  │  RAG Query   │  │  Live Data   │  │  WebSocket   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────────────┐
      │   WEB DASHBOARD (index.html)     │
      │   Real-time Visualizations       │
      │   Chat Interface                 │
      └──────────────────────────────────┘
```

## 📦 Core Components

### 1. **Pathway ETL Pipeline** (`etl_pipeline.py`)
- Real-time data transformation and enrichment
- Rolling window aggregations (15-point windows)
- Feature engineering (anomaly scores, weather conditions)
- Automatic persistence to database
- Batch and stream processing modes

**Key Features:**
```python
pipeline = PathwayETLPipeline(window_size=15)
processed_readings = pipeline.process_batch([sensor_events])
stats = pipeline.get_statistics()
```

### 2. **Vector RAG System** (`vector_rag.py`)
- Semantic document search with embeddings
- Uses `sentence-transformers` (all-MiniLM-L6-v2)
- 384-dimensional vector space, optimized for CPU
- Fallback to rule-based responses when LLM unavailable
- Database-backed chunk storage with similarity scoring

**Key Features:**
```python
rag = VectorRAG(knowledge_dir=Path("knowledge"))
indexed = rag.load_and_index_documents()  # Returns chunk count
results = rag.retrieve(question, top_k=3)  # [RetrievedChunk]
answer = rag.answer(question, live_context)
```

### 3. **Database Layer** (`db.py`)
- SQLAlchemy ORM with async support
- Tables: `sensor_readings`, `processed_features`, `disease_risks`, `rag_documents`, `rag_chunks`
- PostgreSQL (production) or SQLite (development)
- Vector support ready (pgvector extension)

```python
db = DatabaseManager(database_url="postgresql://...")
db.init_sync()
db.create_tables()

session = db.get_session()
readings = session.query(SensorReading).all()
```

### 4. **Streaming Layer** (`streaming.py`)
- **KafkaStreamSource**: Real-time event ingestion from Kafka topics
- **HTTPStreamSource**: REST API polling at configurable intervals
- **FileStreamSource**: Local file processing for testing
- **StreamProcessor**: Orchestrates ETL pipeline + event handlers
- **StreamBuffer**: Batches events before processing

```python
kafka_source = KafkaStreamSource(
    bootstrap_servers="localhost:9092",
    topic="sensor-data"
)
processor = StreamProcessor(kafka_source, etl_pipeline)
processor.add_handler(broadcast_to_websocket)
await processor.start()
```

### 5. **Risk Engine** (`risk_engine.py`)
- Crop-specific disease predictions
- Confidence scoring (0-100)
- Outbreak timing predictions (ETA in hours)
- Actionable recommendations
- Alert triggering on HIGH risk

## 🔧 Installation & Setup

### 1. Install Dependencies
=======
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
>>>>>>> f70cdb55597f196a5314f4f73a2c27e177d0d099
```bash
pip install -r requirements.txt
```

<<<<<<< HEAD
### 2. Database Setup

**SQLite (Development):**
```python
export DATABASE_URL="sqlite:///agriguardian.db"
```

**PostgreSQL (Production):**
```bash
# Create database
createdb agriguardian

# Set connection string
export DATABASE_URL="postgresql://user:password@localhost:5432/agriguardian"
export ASYNC_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/agriguardian"
```

### 3. Initialize RAG Knowledge Base
```bash
# Add markdown files to backend/knowledge/
# Example: disease_management.md, crop_care.md, etc.

# Files are automatically indexed on first startup
```

### 4. Optional: Enable LLM Integration
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
```

### 5. Run Application
```bash
# Development with auto-reload
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.api:app
```

## 📊 Data Flow Examples

### Example 1: Sensor Event Processing
```
Raw Sensor Event
  ↓ (Temperature: 28°C, Humidity: 85%)
Pathway ETL Pipeline
  ↓
Feature Engineering
  ├─ Rolling average (15-point window)
  ├─ Humidity alert detection
  └─ Anomaly scoring
  ↓
Risk Engine
  ├─ Disease prediction (85% confidence)
  ├─ Risk score: 78/100
  └─ Outbreak ETA: 24 hours
  ↓
WebSocket Broadcast
  ↓
Frontend Dashboard Updates
```

### Example 2: Farmer Chat Query
```
Farmer: "My tomatoes have high disease risk. What should I do?"
  ↓
Vector RAG Retrieval
  ├─ Embed question to 384D vector
  ├─ Search rag_chunks table
  └─ Return top-3 semantically similar documents
  ↓
LLM Processing (with retrieved context)
  ├─ GPT-4o-mini generates response
  └─ Fallback: Rule-based if LLM unavailable
  ↓
JSON Response with sources
```

## 🚀 Advanced Usage

### Kafka Integration
```python
from backend.streaming import KafkaStreamSource, StreamProcessor

source = KafkaStreamSource(
    bootstrap_servers="kafka-broker:9092",
    topic="agri-sensors",
    group_id="agriguardian-workers"
)

processor = StreamProcessor(
    source=source,
    etl_pipeline=pipeline,
    batch_size=50
)

# Add custom handlers
processor.add_handler(save_to_datalake)
processor.add_handler(send_alerts)

await processor.start()
```

### Batch Processing with Pathway
```python
import pandas as pd
from backend.etl_pipeline import PathwayETLPipeline

pipeline = PathwayETLPipeline()

# Load data from CSV
data = pd.read_csv("sensor_data.csv")

# Process batch
results = pipeline.process_batch(data.to_dict('records'))

# Access processed features
for reading in results:
    print(f"{reading.crop_type}: Anomaly={reading.anomaly_score}")
```

### RAG Document Management
```python
from backend.vector_rag import VectorRAG

rag = VectorRAG()

# Index documents (loads from knowledge/ directory)
chunk_count = rag.load_and_index_documents()
print(f"Indexed {chunk_count} chunks")

# Retrieve with similarity scores
chunks = rag.retrieve("early blight management", top_k=5)
for chunk in chunks:
    print(f"{chunk.filename}: {chunk.similarity_score}")

# Get full answer with context
answer = rag.answer(
    question="How to prevent late blight?",
    live_context={"crop_type": "potato", "humidity": 92}
)
print(answer["answer"])
print(f"Sources: {answer['sources']}")
```

## 📡 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Service health check |
| `/api/state` | GET | Current state, history, alerts |
| `/api/chat` | POST | RAG-enhanced Q&A |
| `/api/pipeline/stats` | GET | ETL pipeline statistics |
| `/ws` | WebSocket | Real-time telemetry & alerts |

### Example Requests

**Chat Query:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What fungicide should I use for my tomatoes?"}'
```

**Get Pipeline Stats:**
```bash
curl http://localhost:8000/api/pipeline/stats
```

Response:
```json
{
  "sensor_readings": 1250,
  "processed_features": 1250,
  "risk_assessments": 1250,
  "pipeline_status": "active"
}
```

## 🗄️ Database Schema

### sensor_readings
```sql
CREATE TABLE sensor_readings (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  crop_type VARCHAR(50),
  temperature FLOAT,
  humidity FLOAT,
  ... (environmental readings)
)
```

### rag_chunks (with vectors)
```sql
CREATE TABLE rag_chunks (
  id INTEGER PRIMARY KEY,
  document_id INTEGER,
  text TEXT,
  vector VARCHAR(4096),  -- 384D embedding as JSON
  embedding_model VARCHAR(100),
  created_at DATETIME
)
```

## 📈 Performance Optimization

- **Vector Search**: Indexed cosine similarity on 384D embeddings
- **ETL Throughput**: 1000+ events/second with Pathway
- **RAG Latency**: <50ms for chunk retrieval
- **LLM Response**: 1-3 seconds (including API call)

## 🔐 Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///agriguardian.db (dev) or postgresql://... (prod)
DB_ECHO=false

# LLM (Optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Streaming
KAFKA_BROKERS=localhost:9092
KAFKA_TOPIC=sensor-data
```

## 📚 Key Dependencies

- **Pathway**: Streaming ETL framework
- **sentence-transformers**: 384D embeddings (all-MiniLM-L6-v2)
- **SQLAlchemy**: ORM + async support
- **FastAPI**: Web framework
- **OpenAI**: Optional LLM integration
- **Kafka-python**: Message queue support

## ✨ Features

✅ Real-time Pathway ETL pipeline  
✅ Vector embeddings for semantic search  
✅ Database persistence (PostgreSQL/SQLite)  
✅ Kafka/HTTP/File streaming sources  
✅ Crop disease prediction engine  
✅ WebSocket real-time updates  
✅ RAG assistant with LLM fallback  
✅ Production-ready async architecture  
✅ Comprehensive logging & monitoring  
✅ Easy horizontal scaling  

## 📝 License

MIT
=======
### 3) (Optional) Configure LLM access
If you want the assistant to use an LLM, copy the example env file and set your key:

```bash
cp .env.example .env
```
>>>>>>> f70cdb55597f196a5314f4f73a2c27e177d0d099

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
