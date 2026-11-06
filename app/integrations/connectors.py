import os
import re


MANAGED_CONNECTOR_KEYS = frozenset({"amap", "qweather"})


def is_managed_connector(connector_key: str) -> bool:
    return connector_key in MANAGED_CONNECTOR_KEYS


def credential_environment_name(credential_ref: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", (credential_ref or "").strip()).strip("_")
    return f"DATA_CONNECTOR_SECRET_{normalized.upper()}"


def resolve_connector_credential(connector_key: str, credential_ref: str) -> str:
    if connector_key not in MANAGED_CONNECTOR_KEYS:
        return ""
    return os.environ.get(credential_environment_name(credential_ref), "").strip()


def connector_credential_is_configured(connector_key: str, credential_ref: str) -> bool:
    return bool(resolve_connector_credential(connector_key, credential_ref))


def fetch_amap_venue_search(credential: str, parameters: dict, http_get):
    response = http_get(
        "https://restapi.amap.com/v5/place/text",
        params={
            "key": credential,
            "keywords": (parameters.get("keywords") or "").strip(),
            "city": (parameters.get("city") or "").strip(),
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "1":
        raise ValueError("Amap request was rejected")
    return {
        "asset_type": "venue_registry",
        "source_uri": "https://restapi.amap.com/v5/place/text",
        "operation": "venue_search",
        "raw_payload": payload,
        "records": [
            {
                "entity_type": "venue",
                "entity_id": str(poi.get("id") or poi.get("name") or ""),
                "metric_key": "venue_poi",
                "value_json": {
                    "name": poi.get("name") or "",
                    "address": poi.get("address") or "",
                    "location": poi.get("location") or "",
                    "type": poi.get("type") or "",
                    "telephone": poi.get("tel") or "",
                },
                "confidence": 90,
            }
            for poi in payload.get("pois") or []
            if poi.get("id") or poi.get("name")
        ],
    }


def fetch_qweather_daily_forecast(credential: str, parameters: dict, http_get):
    location = (parameters.get("location") or "").strip()
    response = http_get(
        "https://devapi.qweather.com/v7/weather/3d",
        params={"key": credential, "location": location},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "200":
        raise ValueError("QWeather request was rejected")
    return {
        "asset_type": "weather_forecast",
        "source_uri": "https://devapi.qweather.com/v7/weather/3d",
        "operation": "daily_forecast",
        "raw_payload": payload,
        "records": [
            {
                "entity_type": "city",
                "entity_id": location,
                "metric_key": "weather_forecast_daily",
                "value_json": {
                    "date": daily.get("fxDate") or "",
                    "temp_max": int(daily["tempMax"]),
                    "temp_min": int(daily["tempMin"]),
                    "text_day": daily.get("textDay") or "",
                    "text_night": daily.get("textNight") or "",
                    "wind_scale_day": daily.get("windScaleDay") or "",
                    "humidity": int(daily["humidity"]),
                },
                "confidence": 90,
            }
            for daily in payload.get("daily") or []
            if daily.get("fxDate") and daily.get("tempMax") is not None and daily.get("tempMin") is not None
        ],
    }
