"""Example streaming consumer that ingests from various sources."""

import asyncio
import logging
from pathlib import Path

from backend.db import db
from backend.etl_pipeline import PathwayETLPipeline
from backend.streaming import KafkaStreamSource, HTTPStreamSource, FileStreamSource, StreamProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def broadcast_handler(event: dict) -> None:
    """Handle processed events (e.g., send to WebSocket, save to cache)."""
    logger.info(f"Processed event: {event['raw']['crop_type']} - Risk: {event['processed'].risk_score if event['processed'] else 'N/A'}")


async def main_kafka_consumer():
    """Example: Consume from Kafka topic."""
    # Initialize database
    db.init_sync()
    db.create_tables()

    # Create ETL pipeline
    etl_pipeline = PathwayETLPipeline(window_size=15)

    # Create Kafka source
    kafka_source = KafkaStreamSource(
        bootstrap_servers="localhost:9092",
        topic="sensor-data",
        group_id="agriguardian-workers"
    )

    # Create stream processor
    processor = StreamProcessor(
        source=kafka_source,
        etl_pipeline=etl_pipeline,
        batch_size=50
    )

    # Add handler
    processor.add_handler(broadcast_handler)

    # Start consuming
    logger.info("Starting Kafka consumer...")
    await processor.start()


async def main_http_consumer():
    """Example: Poll from HTTP endpoint."""
    db.init_sync()
    db.create_tables()

    etl_pipeline = PathwayETLPipeline(window_size=15)

    http_source = HTTPStreamSource(
        endpoint="http://localhost:8080/api/sensors",
        poll_interval=5
    )

    processor = StreamProcessor(source=http_source, etl_pipeline=etl_pipeline)
    processor.add_handler(broadcast_handler)

    logger.info("Starting HTTP polling consumer...")
    await processor.start()


async def main_file_consumer():
    """Example: Process events from JSONL file."""
    db.init_sync()
    db.create_tables()

    etl_pipeline = PathwayETLPipeline(window_size=15)

    file_source = FileStreamSource(
        file_path="./sensor_data.jsonl",
        batch_size=10
    )

    processor = StreamProcessor(source=file_source, etl_pipeline=etl_pipeline)
    processor.add_handler(broadcast_handler)

    logger.info("Starting file consumer...")
    await processor.start()


if __name__ == "__main__":
    # Choose one of the three:
    # asyncio.run(main_kafka_consumer())
    # asyncio.run(main_http_consumer())
    asyncio.run(main_file_consumer())
