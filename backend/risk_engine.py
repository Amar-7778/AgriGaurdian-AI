from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskResult:
    risk_score: int
    risk_level: str
    reasons: list[str]
    suggested_actions: list[str]
    predicted_disease: str
    disease_confidence: int
    disease_suggestions: list[str]
    outbreak_eta_hours: int
    outbreak_window: str
    forecast_trajectory: list[dict[str, int]]
    action_plan: dict[str, list[str]]
    alert_triggered: bool


class DiseaseRiskEngine:
    def __init__(self) -> None:
        self._last_level = "LOW"

    def _predict_disease(self, features: dict[str, Any], score: int) -> tuple[str, int, list[str]]:
        crop_type = str(features.get("crop_type", "unknown")).lower()
        humidity = float(features.get("humidity", 0))
        temperature = float(features.get("temperature", 0))
        leaf_wetness = float(features.get("leaf_wetness", 0))
        rain_forecast = float(features.get("rain_forecast", 0))

        disease = "General moisture stress"
        confidence = 45
        suggestions = [
            "Inspect the lower canopy for early lesions and discoloration.",
            "Reduce prolonged leaf wetness by improving airflow and irrigation timing.",
        ]

        fungal_window = (
            (humidity > 78 and leaf_wetness > 65)
            or (rain_forecast > 0.55 and leaf_wetness > 60)
            or (score >= 75 and temperature >= 18 and temperature <= 32)
        )

        if fungal_window:
            if crop_type == "tomato":
                disease = "Early blight (Alternaria) risk"
                confidence = 72
                suggestions = [
                    "Remove infected lower leaves and sanitize tools after handling plants.",
                    "Use preventive fungicide strategy with active ingredient rotation.",
                    "Avoid overhead irrigation in late afternoon and evening.",
                ]
            elif crop_type == "potato":
                disease = "Late blight risk"
                confidence = 76
                suggestions = [
                    "Start preventive blight spray schedule based on local advisory guidance.",
                    "Improve field drainage and avoid dense canopy humidity pockets.",
                    "Scout high-risk zones twice daily after rainfall windows.",
                ]
            elif crop_type == "rice":
                disease = "Rice blast risk"
                confidence = 74
                suggestions = [
                    "Avoid excess nitrogen applications during high-risk humid windows.",
                    "Maintain optimal spacing and water management to limit prolonged wetness.",
                    "Apply targeted fungicide only when threshold is confirmed by local guidelines.",
                ]
            elif crop_type == "wheat":
                disease = "Leaf rust risk"
                confidence = 68
                suggestions = [
                    "Increase scouting around dense and shaded sections of the field.",
                    "Prioritize resistant varieties and timely foliar protection if thresholds are met.",
                    "Avoid unnecessary late irrigation that increases canopy humidity.",
                ]
            elif crop_type == "maize":
                disease = "Northern leaf blight risk"
                confidence = 64
                suggestions = [
                    "Scout for elongated gray-green lesions in lower to mid canopy.",
                    "Improve residue management and maintain field airflow.",
                    "Use targeted fungicide only if disease pressure escalates and thresholds are met.",
                ]

        if score >= 75 and disease == "General moisture stress":
            fallback_by_crop = {
                "tomato": "Early blight (Alternaria) risk",
                "potato": "Late blight risk",
                "rice": "Rice blast risk",
                "wheat": "Leaf rust risk",
                "maize": "Northern leaf blight risk",
            }
            disease = fallback_by_crop.get(crop_type, "Fungal disease complex risk")
            confidence = max(confidence, 68)

        confidence = min(95, max(confidence, int(score * 0.85)))
        return disease, confidence, suggestions

    def _estimate_outbreak_eta(self, features: dict[str, Any], score: int) -> tuple[int, str]:
        humidity = float(features.get("humidity", 0))
        rain_forecast = float(features.get("rain_forecast", 0))
        leaf_wetness = float(features.get("leaf_wetness", 0))
        anomaly_score = float(features.get("anomaly_score", 0))

        eta = int(72 - max(0, score - 35) * 1.15)
        if humidity > 80:
            eta -= 8
        if leaf_wetness > 70:
            eta -= 10
        if rain_forecast > 0.65:
            eta -= 8
        if anomaly_score > 1.2:
            eta -= 6

        eta = max(6, min(72, eta))

        if eta <= 12:
            window = "Critical window: within 12 hours"
        elif eta <= 24:
            window = "High probability window: within 24 hours"
        elif eta <= 48:
            window = "Moderate probability window: within 48 hours"
        else:
            window = "Watch window: within 72 hours"
        return eta, window

    def _forecast_trajectory(self, features: dict[str, Any], score: int) -> list[dict[str, int]]:
        humidity = float(features.get("humidity", 0))
        rain_forecast = float(features.get("rain_forecast", 0))
        wind_speed = float(features.get("wind_speed", 0))
        leaf_wetness = float(features.get("leaf_wetness", 0))

        weather_push = 0
        if humidity > 80:
            weather_push += 5
        if rain_forecast > 0.6:
            weather_push += 6
        if leaf_wetness > 70:
            weather_push += 5
        if wind_speed < 2:
            weather_push += 3

        points: list[dict[str, int]] = []
        for horizon in (12, 24, 48, 72):
            decay = int(horizon * 0.22)
            projected = int(score + weather_push - decay)
            projected = max(5, min(100, projected))
            points.append({"hours": horizon, "risk_score": projected})

        return points

    def _build_action_plan(
        self,
        level: str,
        suggested_actions: list[str],
        disease_suggestions: list[str],
    ) -> dict[str, list[str]]:
        do_now: list[str] = []
        today: list[str] = []
        this_week: list[str] = []

        if level == "HIGH":
            do_now = [
                "Trigger high-risk protocol and notify field supervisor.",
                *disease_suggestions[:2],
            ]
            today = [
                *suggested_actions[:2],
                "Capture geo-tagged photos and lesion notes from scouting zones.",
            ]
            this_week = [
                "Review disease progression trend and recalibrate intervention thresholds.",
                "Validate fungicide rotation and compliance with local advisory rules.",
            ]
        elif level == "MEDIUM":
            do_now = [
                "Increase scouting frequency in shaded and low-airflow zones.",
                *suggested_actions[:1],
            ]
            today = [
                *disease_suggestions[:2],
                "Check irrigation timing and avoid late-evening canopy wetness.",
            ]
            this_week = [
                "Track trend consistency before escalating to chemical controls.",
                "Review drainage and canopy management practices for hotspots.",
            ]
        else:
            do_now = ["Maintain routine monitoring and verify sensor calibration."]
            today = ["Inspect representative plots and document baseline crop health."]
            this_week = [
                "Reassess risk thresholds using recent weather and disease observations.",
                "Train field staff on early symptom spotting checklist.",
            ]

        return {
            "do_now": do_now,
            "today": today,
            "this_week": this_week,
        }

    def score(self, features: dict[str, Any]) -> RiskResult:
        score = 0
        reasons: list[str] = []
        actions: list[str] = []

        humidity = float(features.get("humidity", 0))
        temperature = float(features.get("temperature", 0))
        rain_forecast = float(features.get("rain_forecast", 0))
        soil_moisture = float(features.get("soil_moisture", 0))
        wind_speed = float(features.get("wind_speed", 0))
        leaf_wetness = float(features.get("leaf_wetness", 0))
        soil_temperature = float(features.get("soil_temperature", 0))
        soil_ph = float(features.get("soil_ph", 7))
        solar_radiation = float(features.get("solar_radiation", 500))
        crop_type = str(features.get("crop_type", "unknown"))
        anomaly_score = float(features.get("anomaly_score", 0))

        if humidity > 80:
            score += 25
            reasons.append("Humidity is above 80%, creating fungal-friendly conditions.")

        if 20 <= temperature <= 30:
            score += 20
            reasons.append("Temperature is in the 20–30°C fungal growth range.")

        if rain_forecast >= 0.6:
            score += 20
            reasons.append("Rain is forecasted, increasing leaf wetness duration.")

        if leaf_wetness > 70:
            score += 12
            reasons.append("Leaf wetness is elevated, increasing fungal germination likelihood.")

        if soil_moisture > 70:
            score += 10
            reasons.append("Soil moisture is high, supporting pathogen persistence.")

        if wind_speed < 2:
            score += 10
            reasons.append("Low wind speed can reduce canopy drying.")

        if 18 <= soil_temperature <= 28:
            score += 8
            reasons.append("Soil temperature supports disease development dynamics.")

        if not (5.8 <= soil_ph <= 7.2):
            score += 6
            reasons.append("Soil pH is outside the preferred range, increasing plant stress.")

        if humidity > 80 and solar_radiation < 280:
            score += 6
            reasons.append("Low solar radiation with high humidity may prolong canopy wetness.")

        if anomaly_score >= 1.0:
            score += 10
            reasons.append("Recent sensor pattern deviates from rolling baseline.")

        crop_adjustment = {
            "rice": 8,
            "tomato": 8,
            "potato": 6,
            "wheat": 4,
            "maize": 3,
            "cotton": 4,
        }.get(crop_type.lower(), 2)
        score += crop_adjustment

        score = max(0, min(100, score))

        if score >= 75:
            level = "HIGH"
            actions.extend(
                [
                    "Increase field scouting frequency to twice daily.",
                    "Improve air circulation and avoid overhead irrigation.",
                    "Prepare targeted fungicide plan based on local agronomy guidance.",
                ]
            )
        elif score >= 45:
            level = "MEDIUM"
            actions.extend(
                [
                    "Monitor humidity and rainfall windows closely.",
                    "Inspect lower canopy and shaded zones for early signs.",
                    "Optimize irrigation timing for morning-only watering.",
                ]
            )
        else:
            level = "LOW"
            actions.extend(
                [
                    "Continue routine monitoring and maintain hygiene practices.",
                    "Keep drainage and ventilation in good condition.",
                ]
            )

        alert_triggered = level == "HIGH" and self._last_level != "HIGH"
        self._last_level = level
        predicted_disease, disease_confidence, disease_suggestions = self._predict_disease(
            features, score
        )
        outbreak_eta_hours, outbreak_window = self._estimate_outbreak_eta(features, score)
        forecast_trajectory = self._forecast_trajectory(features, score)
        action_plan = self._build_action_plan(level, actions, disease_suggestions)

        return RiskResult(
            risk_score=score,
            risk_level=level,
            reasons=reasons,
            suggested_actions=actions,
            predicted_disease=predicted_disease,
            disease_confidence=disease_confidence,
            disease_suggestions=disease_suggestions,
            outbreak_eta_hours=outbreak_eta_hours,
            outbreak_window=outbreak_window,
            forecast_trajectory=forecast_trajectory,
            action_plan=action_plan,
            alert_triggered=alert_triggered,
        )
