from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass
class ProcessedReading:
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


class StreamingFeaturePipeline:
    def __init__(self, window_size: int = 12) -> None:
        self.window_size = window_size
        self.temperature_window: deque[float] = deque(maxlen=window_size)
        self.humidity_window: deque[float] = deque(maxlen=window_size)
        self.soil_window: deque[float] = deque(maxlen=window_size)
        self.leaf_wetness_window: deque[float] = deque(maxlen=window_size)

    def process(self, payload: dict[str, Any]) -> ProcessedReading:
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

        if humidity_alert and leaf_wetness > 70 and rain_forecast > 0.6 and 20 <= temperature <= 30:
            weather_condition = "Wet-Warm"
        elif temperature > 32 and humidity < 45 and solar_radiation > 650:
            weather_condition = "Heat-Dry"
        else:
            weather_condition = "Stable"

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


def pathway_streaming_table_example() -> None:
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
