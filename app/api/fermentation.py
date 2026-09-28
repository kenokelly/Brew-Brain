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
