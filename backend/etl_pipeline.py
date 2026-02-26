"""Pathway-based ETL pipeline for real-time data processing."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import logging
from dataclasses import dataclass
from statistics import mean
from typing import Any

try:
    import pathway as pw  # type: ignore
except Exception:
    pw = None  # type: ignore

from .db import DiseaseRisk, ProcessedFeature, SensorReading, db

logger = logging.getLogger(__name__)


@dataclass
class SensorEvent:
    """Raw sensor event schema."""
    timestamp: str
    crop_type: str
    temperature: float
    humidity: float
    rain_forecast: float
    soil_moisture: float
    wind_speed: float
    leaf_wetness: float
    soil_temperature: float
    soil_ph: float
    solar_radiation: float


@dataclass
class ProcessedReading:
    """Processed features from streaming pipeline."""
    temperature: float
    humidity: float
    rain_forecast: float
    soil_moisture: float
    wind_speed: float
    leaf_wetness: float
    soil_temperature: float
    soil_ph: float
    solar_radiation: float
    crop_type: str
    rolling_temp_avg: float
    rolling_humidity_avg: float
    rolling_leaf_wetness_avg: float
    humidity_alert: bool
    weather_condition: str
    anomaly_score: float


class PathwayETLPipeline:
    """
    Pathway-based ETL pipeline for processing sensor data in real-time
    with rolling window aggregations, feature engineering, and persistence.
    """

    def __init__(self, window_size: int = 15, db_manager=None):
        self.window_size = window_size
        self.db_manager = db_manager or db
        self.temperature_window: deque[float] = deque(maxlen=window_size)
        self.humidity_window: deque[float] = deque(maxlen=window_size)
        self.soil_window: deque[float] = deque(maxlen=window_size)
        self.leaf_wetness_window: deque[float] = deque(maxlen=window_size)
        self._init_pathway()

    def _init_pathway(self):
        """Initialize Pathway connector and schema."""
        if pw is None or not hasattr(pw, "Schema") or not hasattr(pw, "Column"):
            self.sensor_schema = None
            logger.warning("Pathway runtime is unavailable; using ETL fallback mode.")
            return

        class SensorSchema(pw.Schema):
            timestamp = pw.Column(str)
            crop_type = pw.Column(str)
            temperature = pw.Column(float)
            humidity = pw.Column(float)
            rain_forecast = pw.Column(float)
            soil_moisture = pw.Column(float)
            wind_speed = pw.Column(float)
            leaf_wetness = pw.Column(float)
            soil_temperature = pw.Column(float)
            soil_ph = pw.Column(float)
            solar_radiation = pw.Column(float)

        self.sensor_schema = SensorSchema

    def process_batch(self, events: list[dict[str, Any]]) -> list[ProcessedReading]:
        """Process a batch of sensor events through the ETL pipeline."""
        processed = []
        
        for event in events:
            try:
                reading = self._process_single_event(event)
                sensor_record = self._persist_sensor_reading(event)
                self._persist_processed_feature(reading, sensor_record.id if sensor_record else None)
                processed.append(reading)
            except Exception as e:
                logger.error(f"Error processing event {event}: {e}")
                continue

        return processed

    def process_stream(self, data_stream: list[dict]) -> pw.Table:
        """
        Create a Pathway streaming pipeline from a data stream.
        Useful for integration with message queues (Kafka, RabbitMQ).
        """
        if pw is None or not hasattr(pw, "from_pandas"):
            raise RuntimeError("Pathway runtime is unavailable on this environment.")

        # Convert to list of dicts to Pathway table
        table = pw.from_pandas(
            self._convert_to_dataframe(data_stream)
        ) if data_stream else None

        if table is None:
            return None

        # Apply transformations
        enriched = table.select(
            timestamp=table.timestamp,
            crop_type=table.crop_type,
            temperature=table.temperature,
            humidity=table.humidity,
            rain_forecast=table.rain_forecast,
            soil_moisture=table.soil_moisture,
            wind_speed=table.wind_speed,
            leaf_wetness=table.leaf_wetness,
            soil_temperature=table.soil_temperature,
            soil_ph=table.soil_ph,
            solar_radiation=table.solar_radiation,
            # Add processing timestamp
            processed_at=pw.this.timestamp,
        )

        return enriched

    def _process_single_event(self, payload: dict[str, Any]) -> ProcessedReading:
        """Process a single sensor event through feature engineering."""
        temperature = float(payload["temperature"])
        humidity = float(payload["humidity"])
        rain_forecast = float(payload["rain_forecast"])
        soil_moisture = float(payload["soil_moisture"])
        wind_speed = float(payload["wind_speed"])
        leaf_wetness = float(payload["leaf_wetness"])
        soil_temperature = float(payload["soil_temperature"])
        soil_ph = float(payload["soil_ph"])
        solar_radiation = float(payload["solar_radiation"])
        crop_type = str(payload["crop_type"])

        self.temperature_window.append(temperature)
        self.humidity_window.append(humidity)
        self.soil_window.append(soil_moisture)
        self.leaf_wetness_window.append(leaf_wetness)

        rolling_temp_avg = mean(self.temperature_window)
        rolling_humidity_avg = mean(self.humidity_window)
        rolling_soil_avg = mean(self.soil_window)
        rolling_leaf_wetness_avg = mean(self.leaf_wetness_window)

        humidity_alert = humidity > 80 or rolling_humidity_avg > 78

        # Weather condition classification
        if humidity_alert and leaf_wetness > 70 and rain_forecast > 0.6 and 20 <= temperature <= 30:
            weather_condition = "Wet-Warm"
        elif temperature > 32 and humidity < 45 and solar_radiation > 650:
            weather_condition = "Heat-Dry"
        else:
            weather_condition = "Stable"

        # Anomaly scoring
        anomaly_score = (
            abs(temperature - rolling_temp_avg) / 10
            + abs(humidity - rolling_humidity_avg) / 20
            + abs(soil_moisture - rolling_soil_avg) / 20
            + abs(leaf_wetness - rolling_leaf_wetness_avg) / 20
        )

        return ProcessedReading(
            temperature=temperature,
            humidity=humidity,
            rain_forecast=rain_forecast,
            soil_moisture=soil_moisture,
            wind_speed=wind_speed,
            leaf_wetness=leaf_wetness,
            soil_temperature=soil_temperature,
            soil_ph=soil_ph,
            solar_radiation=solar_radiation,
            crop_type=crop_type,
            rolling_temp_avg=round(rolling_temp_avg, 2),
            rolling_humidity_avg=round(rolling_humidity_avg, 2),
            rolling_leaf_wetness_avg=round(rolling_leaf_wetness_avg, 2),
            humidity_alert=humidity_alert,
            weather_condition=weather_condition,
            anomaly_score=round(anomaly_score, 3),
        )

    def _persist_sensor_reading(self, event: dict[str, Any]) -> SensorReading | None:
        """Persist raw sensor reading to database."""
        session = self.db_manager.get_session()
        try:
            event_timestamp = event.get("timestamp")
            parsed_timestamp: datetime | None = None
            if isinstance(event_timestamp, str):
                parsed_timestamp = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
            elif isinstance(event_timestamp, datetime):
                parsed_timestamp = event_timestamp

            reading = SensorReading(
                timestamp=parsed_timestamp or datetime.now(timezone.utc),
                crop_type=event.get("crop_type"),
                temperature=float(event.get("temperature", 0)),
                humidity=float(event.get("humidity", 0)),
                rain_forecast=float(event.get("rain_forecast", 0)),
                soil_moisture=float(event.get("soil_moisture", 0)),
                wind_speed=float(event.get("wind_speed", 0)),
                leaf_wetness=float(event.get("leaf_wetness", 0)),
                soil_temperature=float(event.get("soil_temperature", 0)),
                soil_ph=float(event.get("soil_ph", 0)),
                solar_radiation=float(event.get("solar_radiation", 0)),
            )
            session.add(reading)
            session.commit()
            session.refresh(reading)
            return reading
        except Exception as e:
            logger.error(f"Error persisting sensor reading: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def _persist_processed_feature(self, processed: ProcessedReading, sensor_reading_id: int | None) -> None:
        """Persist processed features to database."""
        session = self.db_manager.get_session()
        try:
            feature = ProcessedFeature(
                sensor_reading_id=sensor_reading_id,
                crop_type=processed.crop_type,
                rolling_temp_avg=processed.rolling_temp_avg,
                rolling_humidity_avg=processed.rolling_humidity_avg,
                rolling_leaf_wetness_avg=processed.rolling_leaf_wetness_avg,
                humidity_alert=str(processed.humidity_alert),
                weather_condition=processed.weather_condition,
                anomaly_score=processed.anomaly_score,
            )
            session.add(feature)
            session.commit()
        except Exception as e:
            logger.error(f"Error persisting processed feature: {e}")
            session.rollback()
        finally:
            session.close()

    def _convert_to_dataframe(self, data_stream: list[dict]):
        """Convert data stream to pandas DataFrame for Pathway processing."""
        import pandas as pd
        return pd.DataFrame(data_stream)

    def get_statistics(self) -> dict[str, Any]:
        """Get ETL pipeline statistics."""
        session = self.db_manager.get_session()
        try:
            sensor_count = session.query(SensorReading).count()
            feature_count = session.query(ProcessedFeature).count()
            risk_count = session.query(DiseaseRisk).count()

            return {
                "sensor_readings": sensor_count,
                "processed_features": feature_count,
                "risk_assessments": risk_count,
                "pipeline_status": "active"
            }
        finally:
            session.close()
