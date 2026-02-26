"""Example batch processing with Pathway ETL pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.db import db
from backend.etl_pipeline import PathwayETLPipeline


def example_batch_processing():
    """Process a batch of sensor readings from CSV or JSON."""

    # Initialize database
    db.init_sync()
    db.create_tables()

    # Create ETL pipeline
    pipeline = PathwayETLPipeline(window_size=15)

    # Example sensor data (from file or API)
    sensor_events = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "crop_type": "tomato",
            "temperature": 28.5,
            "humidity": 82.0,
            "rain_forecast": 0.65,
            "soil_moisture": 65.0,
            "wind_speed": 3.2,
            "leaf_wetness": 75.0,
            "soil_temperature": 25.0,
            "soil_ph": 6.8,
            "solar_radiation": 450.0,
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "crop_type": "potato",
            "temperature": 22.0,
            "humidity": 88.0,
            "rain_forecast": 0.72,
            "soil_moisture": 70.0,
            "wind_speed": 2.1,
            "leaf_wetness": 82.0,
            "soil_temperature": 19.5,
            "soil_ph": 6.2,
            "solar_radiation": 380.0,
        },
    ]

    # Process batch
    processed_readings = pipeline.process_batch(sensor_events)

    # Print results
    for i, reading in enumerate(processed_readings):
        print(f"\n--- Event {i+1} ---")
        print(f"Crop: {reading.crop_type}")
        print(f"Temperature: {reading.temperature}°C")
        print(f"Rolling Temp Avg: {reading.rolling_temp_avg}°C")
        print(f"Humidity: {reading.humidity}%")
        print(f"Rolling Humidity Avg: {reading.rolling_humidity_avg}%")
        print(f"Weather Condition: {reading.weather_condition}")
        print(f"Humidity Alert: {reading.humidity_alert}")
        print(f"Anomaly Score: {reading.anomaly_score}")

    # Get pipeline statistics
    stats = pipeline.get_statistics()
    print(f"\n--- Pipeline Statistics ---")
    print(json.dumps(stats, indent=2))


def example_load_from_csv():
    """Load sensor data from CSV and process."""
    import pandas as pd

    db.init_sync()
    db.create_tables()

    pipeline = PathwayETLPipeline(window_size=15)

    # Load CSV
    df = pd.read_csv("sensor_data.csv")

    # Convert to list of dicts
    events = df.to_dict('records')

    # Process
    results = pipeline.process_batch(events)

    # Save results to CSV
    output_df = pd.DataFrame([r.__dict__ for r in results])
    output_df.to_csv("processed_features.csv", index=False)

    print(f"Processed {len(results)} events. Results saved to processed_features.csv")


def example_rag_system():
    """Example of using Vector RAG system."""
    from backend.vector_rag import VectorRAG

    # Initialize RAG
    rag = VectorRAG(knowledge_dir=Path("backend/knowledge"))

    # Load and index documents
    chunk_count = rag.load_and_index_documents()
    print(f"Indexed {chunk_count} chunks from knowledge base")

    # Retrieve documents
    question = "How do I prevent early blight on tomatoes?"
    results = rag.retrieve(question, top_k=3)

    print(f"\nTop results for: {question}")
    for i, chunk in enumerate(results):
        print(f"\n{i+1}. {chunk.filename} (Similarity: {chunk.similarity_score})")
        print(f"   {chunk.text[:200]}...")

    # Get RAG answer
    live_context = {
        "crop_type": "tomato",
        "humidity": 85,
        "temperature": 28,
        "risk_level": "HIGH",
        "risk_score": 78,
    }

    answer = rag.answer(question, live_context)
    print(f"\n--- RAG Answer ---")
    print(f"Answer: {answer['answer']}")
    print(f"Sources: {answer['sources']}")
    print(f"Confidence: {answer['confidence']}")
    print(f"Method: {answer['method']}")


if __name__ == "__main__":
    print("=" * 60)
    print("AgriGuardian AI - Batch Processing Examples")
    print("=" * 60)

    print("\n1. Batch Processing Example")
    print("-" * 60)
    example_batch_processing()

    print("\n2. RAG System Example")
    print("-" * 60)
    example_rag_system()

    # Uncomment to test CSV processing
    # example_load_from_csv()
