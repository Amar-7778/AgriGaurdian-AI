"""Legacy pathway pipeline kept for backward compatibility."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import mean
from typing import Any

# Import from new ETL pipeline
from .etl_pipeline import ProcessedReading, PathwayETLPipeline


class StreamingFeaturePipeline:
    """
    Backward-compatible wrapper around PathwayETLPipeline.
    Maintains original interface while using new Pathway-based ETL system.
    """

    def __init__(self, window_size: int = 12) -> None:
        self.window_size = window_size
        self.etl_pipeline = PathwayETLPipeline(window_size=window_size)
        self.temperature_window: deque[float] = deque(maxlen=window_size)
        self.humidity_window: deque[float] = deque(maxlen=window_size)
        self.soil_window: deque[float] = deque(maxlen=window_size)
        self.leaf_wetness_window: deque[float] = deque(maxlen=window_size)

    def process(self, payload: dict[str, Any]) -> ProcessedReading:
        """Process event through the ETL pipeline."""
        return self.etl_pipeline._process_single_event(payload)


def pathway_streaming_table_example() -> None:
    """Example of using Pathway's streaming table API for reference."""
    import pathway as pw

    class SensorSchema(pw.Schema):
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

    table = pw.debug.table_from_markdown(
        """
        crop_type | temperature | humidity | rain_forecast | soil_moisture | wind_speed | leaf_wetness | soil_temperature | soil_ph | solar_radiation
        tomato    | 27.0        | 84.0     | 0.70          | 72.0          | 1.2        | 78.0         | 24.8             | 6.4     | 310.0
        wheat     | 24.0        | 62.0     | 0.20          | 48.0          | 3.8        | 42.0         | 21.9             | 7.1     | 720.0
        rice      | 29.0        | 88.0     | 0.82          | 80.0          | 1.0        | 88.0         | 26.2             | 6.1     | 250.0
        """,
        schema=SensorSchema,
    )

    transformed = table.select(
        pw.this.crop_type,
        pw.this.temperature,
        pw.this.humidity,
        pw.this.rain_forecast,
        pw.this.leaf_wetness,
        pw.this.soil_temperature,
        pw.this.soil_ph,
        pw.this.solar_radiation,
        humidity_alert=pw.this.humidity > 80,
        fungal_condition=(pw.this.humidity > 80)
        & (pw.this.temperature >= 20)
        & (pw.this.temperature <= 30)
        & (pw.this.rain_forecast > 0.6)
        & (pw.this.leaf_wetness > 70),
    )

    aggregated = transformed.reduce(
        records=pw.reducers.count(),
        avg_humidity=pw.reducers.avg(transformed.humidity),
        avg_leaf_wetness=pw.reducers.avg(transformed.leaf_wetness),
        alert_records=pw.reducers.sum(pw.cast(int, transformed.humidity_alert)),
    )

    pw.debug.compute_and_print(transformed, include_id=False)
    pw.debug.compute_and_print(aggregated, include_id=False)


if __name__ == "__main__":
    pathway_streaming_table_example()
