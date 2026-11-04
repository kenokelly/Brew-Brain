"""
Flask blueprint for receiving ESP32 telemetry (Keg Scales & Flow Meters).

Endpoints:
- POST /api/automation/telemetry/scale
- POST /api/automation/telemetry/flow
"""

from typing import Tuple
from flask import Blueprint, request, Response
from api.routes import api_response, handle_error
from core.config import logger, get_config, set_config
from services.scale_processor import calculate_keg_volume
from services.flow_manager import process_pour_event

telemetry_receiver_bp = Blueprint("telemetry_receiver", __name__)


@telemetry_receiver_bp.route("/scale", methods=["POST"])
def receive_scale_telemetry() -> Tuple[Response, int]:
    """
    Ingest keg scale weight telemetry from ESP32 load cell nodes.

    Expects JSON:
    {
        "tap_id": "tap1",
        "sensor_id": "scale_esp32_01",
        "weight_kg": 23.5,
        "tare_weight_kg": 4.5, (optional)
        "battery_v": 4.12, (optional)
        "rssi": -65 (optional)
    }
    """
    try:
        data = request.json or {}
        tap_id = data.get("tap_id")
        weight_kg = data.get("weight_kg")

        if not tap_id:
            return api_response(status="error", error="Missing tap_id", code=400)
        if weight_kg is None:
            return api_response(status="error", error="Missing weight_kg", code=400)

        try:
            weight_kg = float(weight_kg)
        except (ValueError, TypeError):
            return api_response(status="error", error="weight_kg must be a number", code=400)

        tare_weight_kg = data.get("tare_weight_kg", 4.5)
        try:
            tare_weight_kg = float(tare_weight_kg)
        except (ValueError, TypeError):
            tare_weight_kg = 4.5

        # Get tap config to check FG and keg capacity
        taps = get_config("taps") or {}
        tap = taps.get(tap_id, {})
        sg = float(tap.get("fg", 1.010)) if isinstance(tap, dict) else 1.010
        keg_capacity_l = float(tap.get("keg_volume_l", 19.0)) if isinstance(tap, dict) else 19.0

        # Calculate volume metrics
        processed = calculate_keg_volume(
            raw_weight_kg=weight_kg,
            tare_weight_kg=tare_weight_kg,
            sg=sg,
            keg_capacity_l=keg_capacity_l,
        )

        # Update tap state if tap exists
        if tap_id in taps and isinstance(taps[tap_id], dict):
            taps[tap_id]["volume_remaining_ml"] = processed["volume_remaining_ml"]
            taps[tap_id]["remaining_pct"] = processed["remaining_pct"]
            taps[tap_id]["keg_remaining"] = processed["volume_remaining_l"]
            set_config("taps", taps)

        # Record to InfluxDB if available
        try:
            from core.influx import write_api, INFLUX_BUCKET
            from influxdb_client import Point

            if write_api:
                point = (
                    Point("keg_scale_readings")
                    .tag("tap_id", str(tap_id))
                    .tag("sensor_id", str(data.get("sensor_id", "unknown")))
                    .field("weight_kg", processed["raw_weight_kg"])
                    .field("net_weight_kg", processed["net_weight_kg"])
                    .field("volume_remaining_l", processed["volume_remaining_l"])
                    .field("remaining_pct", processed["remaining_pct"])
                )
                if "battery_v" in data:
                    point.field("battery_v", float(data["battery_v"]))
                if "rssi" in data:
                    point.field("rssi", int(data["rssi"]))

                write_api.write(bucket=INFLUX_BUCKET, record=point)
        except Exception as e:
            logger.debug(f"InfluxDB write skipped for scale telemetry: {e}")

        return api_response(data={"tap_id": tap_id, "processed": processed})

    except Exception as e:
        return handle_error(e, "Keg Scale Telemetry Error")


@telemetry_receiver_bp.route("/flow", methods=["POST"])
def receive_flow_telemetry() -> Tuple[Response, int]:
    """
    Ingest inline flow meter pour telemetry from ESP32 flow nodes.

    Expects JSON:
    {
        "tap_id": "tap1",
        "sensor_id": "flow_esp32_01",
        "pulse_count": 3340,
        "volume_ml": 568.0, (optional)
        "duration_sec": 12.4 (optional)
    }
    """
    try:
        data = request.json or {}
        tap_id = data.get("tap_id")
        pulse_count = data.get("pulse_count")

        if not tap_id:
            return api_response(status="error", error="Missing tap_id", code=400)
        if pulse_count is None:
            return api_response(status="error", error="Missing pulse_count", code=400)

        try:
            pulse_count = int(pulse_count)
        except (ValueError, TypeError):
            return api_response(status="error", error="pulse_count must be an integer", code=400)

        volume_ml = data.get("volume_ml")
        if volume_ml is not None:
            try:
                volume_ml = float(volume_ml)
            except (ValueError, TypeError):
                volume_ml = None

        duration_sec = data.get("duration_sec", 0.0)
        try:
            duration_sec = float(duration_sec)
        except (ValueError, TypeError):
            duration_sec = 0.0

        # Process pour event
        result = process_pour_event(
            tap_id=tap_id,
            pulse_count=pulse_count,
            volume_ml=volume_ml,
            duration_sec=duration_sec,
        )

        # Write to InfluxDB if successfully processed
        if result.get("status") == "success":
            try:
                from core.influx import write_api, INFLUX_BUCKET
                from influxdb_client import Point

                if write_api:
                    point = (
                        Point("flow_meter_readings")
                        .tag("tap_id", str(tap_id))
                        .tag("sensor_id", str(data.get("sensor_id", "unknown")))
                        .field("pulse_count", pulse_count)
                        .field("volume_ml", result["volume_ml"])
                        .field("duration_sec", duration_sec)
                        .field("new_remaining_pct", result["new_remaining_pct"])
                    )
                    write_api.write(bucket=INFLUX_BUCKET, record=point)
            except Exception as e:
                logger.debug(f"InfluxDB write skipped for flow telemetry: {e}")

        return api_response(data=result)

    except Exception as e:
        return handle_error(e, "Flow Telemetry Error")
