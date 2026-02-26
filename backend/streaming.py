"""Streaming data handlers for real-time ingestion from various sources."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from .etl_pipeline import PathwayETLPipeline

logger = logging.getLogger(__name__)


class StreamSource(ABC):
    """Abstract base class for data stream sources."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the data source."""
        pass

    @abstractmethod
    async def read_events(self) -> Any:
        """Read events from the source."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass


class KafkaStreamSource(StreamSource):
    """Kafka stream source for real-time sensor data ingestion."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "sensor-data",
        group_id: str = "agriguardian-consumer"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = None

    async def connect(self) -> None:
        """Connect to Kafka broker."""
        try:
            from kafka import KafkaConsumer
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                auto_offset_reset="earliest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=30000
            )
            logger.info(f"Connected to Kafka topic: {self.topic}")
        except ImportError:
            logger.error("kafka-python not installed")
            raise

    async def read_events(self):
        """Read and yield events from Kafka stream."""
        if self.consumer is None:
            await self.connect()

        try:
            for message in self.consumer:
                yield message.value
        except Exception as e:
            logger.error(f"Error reading from Kafka: {e}")

    async def close(self) -> None:
        """Close Kafka consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


class HTTPStreamSource(StreamSource):
    """HTTP polling source for REST API sensor data."""

    def __init__(self, endpoint: str, poll_interval: int = 5):
        self.endpoint = endpoint
        self.poll_interval = poll_interval
        self.session = None

    async def connect(self) -> None:
        """Establish HTTP session."""
        try:
            import httpx
            self.session = httpx.AsyncClient()
            logger.info(f"Connected to HTTP endpoint: {self.endpoint}")
        except ImportError:
            logger.error("httpx not installed")
            raise

    async def read_events(self):
        """Poll HTTP endpoint and yield events."""
        if self.session is None:
            await self.connect()

        while True:
            try:
                response = await self.session.get(self.endpoint)
                response.raise_for_status()
                data = response.json()

                # Assume data is a list of events or a single event
                if isinstance(data, list):
                    for event in data:
                        yield event
                else:
                    yield data

                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error polling HTTP endpoint: {e}")
                await asyncio.sleep(self.poll_interval)

    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()
            logger.info("HTTP session closed")


class FileStreamSource(StreamSource):
    """File-based stream source for testing and local development."""

    def __init__(self, file_path: str, batch_size: int = 10):
        self.file_path = file_path
        self.batch_size = batch_size
        self.file = None

    async def connect(self) -> None:
        """Open file for reading."""
        try:
            self.file = open(self.file_path, "r")
            logger.info(f"Opened file stream: {self.file_path}")
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            raise

    async def read_events(self):
        """Read events from file (one JSON per line)."""
        if self.file is None:
            await self.connect()

        try:
            for line in self.file:
                line = line.strip()
                if line:
                    event = json.loads(line)
                    yield event
        except Exception as e:
            logger.error(f"Error reading from file: {e}")

    async def close(self) -> None:
        """Close file."""
        if self.file:
            self.file.close()
            logger.info("File stream closed")


class StreamProcessor:
    """
    Central stream processor that reads from source,
    processes through ETL pipeline, and calls handlers.
    """

    def __init__(
        self,
        source: StreamSource,
        etl_pipeline: PathwayETLPipeline,
        batch_size: int = 10
    ):
        self.source = source
        self.etl_pipeline = etl_pipeline
        self.batch_size = batch_size
        self.handlers: list[Callable[[dict[str, Any]], None]] = []
        self.running = False

    def add_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Add a handler to be called for each processed event."""
        self.handlers.append(handler)

    async def start(self) -> None:
        """Start processing stream."""
        await self.source.connect()
        self.running = True

        try:
            async for event in self._event_stream():
                # Process through ETL pipeline
                try:
                    processed = self.etl_pipeline.process_batch([event])
                    
                    # Call all handlers with processed data
                    for handler in self.handlers:
                        await self._call_handler(handler, {
                            "raw": event,
                            "processed": processed[0].__dict__ if processed else None
                        })
                except Exception as e:
                    logger.error(f"Error processing event: {e}")

        except asyncio.CancelledError:
            logger.info("Stream processing cancelled")
        finally:
            await self.stop()

    async def _event_stream(self):
        """Async generator wrapper for source events."""
        async for event in self.source.read_events():
            yield event

    async def _call_handler(self, handler: Callable, event: dict[str, Any]) -> None:
        """Call handler, supporting both sync and async."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Error in handler: {e}")

    async def stop(self) -> None:
        """Stop processing stream."""
        self.running = False
        await self.source.close()
        logger.info("Stream processor stopped")


class StreamBuffer:
    """Buffer for batching stream events before processing."""

    def __init__(self, max_size: int = 100, timeout: float = 5.0):
        self.max_size = max_size
        self.timeout = timeout
        self.buffer: list[dict[str, Any]] = []
        self.last_flush = asyncio.get_event_loop().time()

    def add(self, event: dict[str, Any]) -> bool:
        """Add event to buffer. Returns True if buffer should be flushed."""
        self.buffer.append(event)
        
        if len(self.buffer) >= self.max_size:
            return True
        
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_flush >= self.timeout:
            return True
        
        return False

    def flush(self) -> list[dict[str, Any]]:
        """Get and clear buffer."""
        result = self.buffer[:]
        self.buffer.clear()
        self.last_flush = asyncio.get_event_loop().time()
        return result

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.buffer) == 0
