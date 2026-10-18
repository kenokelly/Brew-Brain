from typing import Tuple
from flask import Blueprint, Response, request
from core.auth import require_api_token
from api.routes import api_response, handle_error

fermentation_bp = Blueprint('fermentation', __name__)


@fermentation_bp.route('/summary')
def summary() -> Tuple[Response, int]:
    """Live fermentation card data: gravity, velocity, phase, ETA, step timeline."""
    try:
        from services.fermentation import get_fermentation_summary
        return api_response(data=get_fermentation_summary())
    except Exception as e:
        return handle_error(e, "Fermentation summary error")


@fermentation_bp.route('/history')
def history() -> Tuple[Response, int]:
    """Downsampled gravity/temp/target/velocity/ABV series since pitch."""
    try:
        from services.fermentation import get_fermentation_history
        return api_response(data=get_fermentation_history())
    except Exception as e:
        return handle_error(e, "Fermentation history error")


@fermentation_bp.route('/journal', methods=['GET'])
def journal() -> Tuple[Response, int]:
    try:
        from services.journal import list_entries
        limit = request.args.get('limit', default=50, type=int)
        return api_response(data={"entries": list_entries(limit)})
    except Exception as e:
        return handle_error(e, "Journal error")


@fermentation_bp.route('/journal', methods=['POST'])
@require_api_token
def add_journal_note() -> Tuple[Response, int]:
    """Manual note, e.g. 'dry hops in' or 'hydrometer FG 1.012'."""
    try:
        from services.journal import add_entry
        text = str((request.get_json(silent=True) or {}).get('text', '')).strip()
        if not text:
            return api_response(status="error", error="text is required", code=400)
        if len(text) > 500:
            return api_response(status="error", error="text must be 500 characters or fewer", code=400)
        entry = add_entry(text, kind="note", dedupe_minutes=0)
        return api_response(data={"entry": entry}, code=201)
    except Exception as e:
        return handle_error(e, "Journal note error")


@fermentation_bp.route('/water-test', methods=['POST'])
@require_api_token
def water_test() -> Tuple[Response, int]:
    """Start/stop the water test, or apply its suggested Tilt offset.

    Body: {"action": "start" | "stop" | "apply_offset"}
    """
    try:
        from core.config import get_config, set_config
        from services.fermentation import get_water_test_calibration
        from services.journal import add_entry

        action = (request.get_json(silent=True) or {}).get('action')
        if action == 'start':
            set_config('water_test', True)
            add_entry("Water test started: Tilt in plain water, fermentation alerts paused", kind="info", dedupe_minutes=0)
            return api_response(data={"water_test": True})
        if action == 'stop':
            set_config('water_test', False)
            from datetime import datetime, timezone
            set_config('water_test_ended', datetime.now(timezone.utc).isoformat())
            add_entry("Water test ended: fermentation alerts back on", kind="info", dedupe_minutes=0)
            return api_response(data={"water_test": False})
        if action == 'apply_offset':
            if not get_config('water_test'):
                return api_response(status="error", error="Start a water test first", code=409)
            cal = get_water_test_calibration()
            if cal.get("status") != "ready":
                return api_response(status="error", error=cal.get("message") or "Not ready to calibrate", code=409, data=cal)
            old = float(get_config('offset') or 0.0)
            set_config('offset', cal["suggested_offset"])
            add_entry(f"Tilt calibrated in water: offset {old:+.3f} → {cal['suggested_offset']:+.3f} "
                      f"(raw {cal['raw_mean']:.4f})", kind="note", dedupe_minutes=0)
            return api_response(data={"offset": cal["suggested_offset"], "previous_offset": old})
        return api_response(status="error", error="action must be start, stop or apply_offset", code=400)
    except Exception as e:
        return handle_error(e, "Water test error")


@fermentation_bp.route('/log-start', methods=['POST'])
@require_api_token
def log_start() -> Tuple[Response, int]:
    """Start the charts from now, hiding earlier readings, or go back to the batch start.

    Body: {"action": "start" | "whole_batch" | "since_log_start", "at": optional ISO time for start}
    "whole_batch" / "since_log_start" only switch the chart view; the mark is kept.
    """
    try:
        from datetime import datetime, timezone
        from core.config import set_config
        from services.journal import add_entry

        body = request.get_json(silent=True) or {}
        action = body.get('action')
        if action == 'start':
            now = datetime.now(timezone.utc)
            start = now
            if body.get('at'):
                try:
                    start = datetime.fromisoformat(str(body['at']).replace('Z', '+00:00'))
                except ValueError:
                    return api_response(status="error", error="at must be an ISO date-time", code=400)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if start > now:
                    return api_response(status="error", error="at can't be in the future", code=400)
            set_config('log_start', start.isoformat())
            set_config('log_whole_batch', False)
            add_entry(f"Log restarted: charts now start from {start.strftime('%d %b %H:%M')} UTC", kind="info", dedupe_minutes=0)
            return api_response(data={"log_start": start.isoformat()})
        if action in ('whole_batch', 'clear'):
            set_config('log_whole_batch', True)
            return api_response(data={"whole_batch": True})
        if action == 'since_log_start':
            set_config('log_whole_batch', False)
            return api_response(data={"whole_batch": False})
        return api_response(status="error", error="action must be start, whole_batch or since_log_start", code=400)
    except Exception as e:
        return handle_error(e, "Log start error")
