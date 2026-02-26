"""Database management module for persistent storage and vector search."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

# Database URL from environment or default to SQLite for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./agriguardian.db"
)

# For async operations
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    "sqlite+aiosqlite:///./agriguardian.db"
)

Base = declarative_base()


class SensorReading(Base):
    """Raw sensor data readings from ETL pipeline."""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    crop_type = Column(String(50), index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    rain_forecast = Column(Float)
    soil_moisture = Column(Float)
    wind_speed = Column(Float)
    leaf_wetness = Column(Float)
    soil_temperature = Column(Float)
    soil_ph = Column(Float)
    solar_radiation = Column(Float)


class ProcessedFeature(Base):
    """Processed features from streaming pipeline."""
    __tablename__ = "processed_features"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    sensor_reading_id = Column(Integer, index=True)
    crop_type = Column(String(50), index=True)
    rolling_temp_avg = Column(Float)
    rolling_humidity_avg = Column(Float)
    rolling_leaf_wetness_avg = Column(Float)
    humidity_alert = Column(String(10))
    weather_condition = Column(String(50))
    anomaly_score = Column(Float)


class DiseaseRisk(Base):
    """Disease risk scoring results."""
    __tablename__ = "disease_risks"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    feature_id = Column(Integer, index=True)
    crop_type = Column(String(50), index=True)
    risk_score = Column(Integer)
    risk_level = Column(String(20), index=True)
    predicted_disease = Column(String(200))
    disease_confidence = Column(Integer)
    outbreak_eta_hours = Column(Integer)
    reasons = Column(Text)
    suggested_actions = Column(Text)
    alert_triggered = Column(String(5))


class RAGDocument(Base):
    """Documents for RAG system with vector embeddings."""
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True)
    content = Column(Text)
    content_hash = Column(String(64), unique=True)
    indexed_at = Column(DateTime, default=datetime.now(timezone.utc))


class RAGChunk(Base):
    """Text chunks from documents with embeddings for vector search."""
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    chunk_index = Column(Integer)
    text = Column(Text)
    vector = Column(String)  # Stored as JSON string for flexibility
    embedding_model = Column(String(100))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None

    def init_sync(self) -> None:
        """Initialize synchronous database connection."""
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Enable pgvector extension for PostgreSQL if needed
        if "postgresql" in self.database_url:
            with self.engine.connect() as conn:
                try:
                    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.commit()
                except Exception:
                    pass

    async def init_async(self) -> None:
        """Initialize asynchronous database connection."""
        self.async_engine = create_async_engine(
            ASYNC_DATABASE_URL,
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )
        self.AsyncSessionLocal = sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    def create_tables(self) -> None:
        """Create all tables in the database."""
        if self.engine is None:
            self.init_sync()
        Base.metadata.create_all(bind=self.engine)

    async def create_tables_async(self) -> None:
        """Create all tables asynchronously."""
        if self.async_engine is None:
            await self.init_async()
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def get_session(self):
        """Get a synchronous database session."""
        if self.SessionLocal is None:
            self.init_sync()
        return self.SessionLocal()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an asynchronous database session."""
        if self.AsyncSessionLocal is None:
            await self.init_async()
        async with self.AsyncSessionLocal() as session:
            yield session

    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()


# Global instance
db = DatabaseManager()
