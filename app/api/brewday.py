"""
Flask blueprint for the AI Brew Day Coach API.

Provides endpoints for managing brew day sessions: starting/ending sessions,
recording gravity readings, getting AI coaching responses, computing corrections,
and managing timers.
"""

from typing import Tuple

from flask import Blueprint, request, Response
from api.routes import api_response, handle_error
from core.config import logger

brewday_bp = Blueprint("brewday", __name__)


@brewday_bp.route("/start", methods=["POST"])
def start_session() -> Tuple[Response, int]:
    """
    Start a new brew day session.

    Expects JSON: {"batch_id": str, "recipe": dict}
    """
    try:
        data = request.json or {}
        batch_id = data.get("batch_id")
        recipe = data.get("recipe")

        if not batch_id:
            return api_response(status="error", error="Missing batch_id", code=400)
        if not recipe or not isinstance(recipe, dict):
            return api_response(status="error", error="Missing or invalid recipe", code=400)

        from services.brewday_coach import BrewSessionManager

        manager = BrewSessionManager()
        session = manager.start_session(batch_id, recipe)
        return api_response(data=session)

    except Exception as e:
        return handle_error(e, "Brew Day Start Error")


@brewday_bp.route("/state", methods=["GET"])
def get_state() -> Tuple[Response, int]:
    """
    Get the current session state.

    Query param: ?batch_id=xxx
    """
    try:
        batch_id = request.args.get("batch_id")
        if not batch_id:
            return api_response(status="error", error="Missing batch_id", code=400)

        from services.brewday_coach import BrewSessionManager

        manager = BrewSessionManager()
        state = manager.get_current_state(batch_id)

        if state is None:
            return api_response(
                status="error",
                error=f"No active session for batch_id={batch_id}",
                code=404,
            )

        return api_response(data=state)

    except Exception as e:
        return handle_error(e, "Brew Day State Error")


@brewday_bp.route("/action", methods=["POST"])
def session_action() -> Tuple[Response, int]:
    """
    Perform a session action.

    Expects JSON: {"batch_id": str, "action_type": str, "message": str}
    Actions:
        - "chat": AI coaching response
        - "advance": Advance to next phase
        - "timer": Add a timer (requires name, duration_min, addition_type in message or data)
    """
    try:
        data = request.json or {}
        batch_id = data.get("batch_id")
        action_type = data.get("action_type")

        if not batch_id:
            return api_response(status="error", error="Missing batch_id", code=400)
        if not action_type:
            return api_response(status="error", error="Missing action_type", code=400)

        from services.brewday_coach import BrewSessionManager

        manager = BrewSessionManager()

        if action_type == "chat":
            message = data.get("message", "")
            if not message:
                return api_response(
                    status="error", error="Missing message for chat action", code=400
                )

            session = manager.get_current_state(batch_id)
            if session is None:
                return api_response(
                    status="error",
                    error=f"No active session for batch_id={batch_id}",
                    code=404,
                )

            from services.ai import generate_brewday_coaching_response

            result = generate_brewday_coaching_response(session, message)
            return api_response(data=result)

        elif action_type == "advance":
            session = manager.advance_step(batch_id)
            return api_response(data=session)

        elif action_type == "timer":
            name = data.get("name", "Timer")
            duration_min = data.get("duration_min", 60)
            addition_type = data.get("addition_type", "general")

            try:
                duration_min = int(duration_min)
            except (ValueError, TypeError):
                return api_response(
                    status="error", error="duration_min must be an integer", code=400
                )

            timer = manager.add_timer(batch_id, name, duration_min, addition_type)
            return api_response(data=timer)

        else:
            return api_response(
                status="error",
                error=f"Unknown action_type: {action_type}. Must be 'chat', 'advance', or 'timer'.",
                code=400,
            )

    except ValueError as e:
        return api_response(status="error", error=str(e), code=400)
    except Exception as e:
        return handle_error(e, "Brew Day Action Error")


@brewday_bp.route("/correct", methods=["POST"])
def correct_gravity() -> Tuple[Response, int]:
    """
    Record a gravity reading, compute corrections, and return an AI explanation.

    Expects JSON: {"batch_id": str, "measured_sg": float, "measured_volume": float, "stage": str}
    """
    try:
        data = request.json or {}
        batch_id = data.get("batch_id")
        measured_sg = data.get("measured_sg")
        measured_volume = data.get("measured_volume")
        stage = data.get("stage", "pre_boil")

        if not batch_id:
            return api_response(status="error", error="Missing batch_id", code=400)
        if measured_sg is None:
            return api_response(status="error", error="Missing measured_sg", code=400)
        if measured_volume is None:
            return api_response(
                status="error", error="Missing measured_volume", code=400
            )

        try:
            measured_sg = float(measured_sg)
            measured_volume = float(measured_volume)
        except (ValueError, TypeError):
            return api_response(
                status="error",
                error="measured_sg and measured_volume must be numbers",
                code=400,
            )

        from services.brewday_coach import BrewSessionManager

        manager = BrewSessionManager()
        reading = manager.record_gravity_reading(
            batch_id, measured_sg, measured_volume, stage
        )

        # If corrections were computed, get an AI explanation
        corrections = reading.get("corrections", {})
        explanation = None
        if corrections:
            from services.ai import generate_correction_explanation

            explanation = generate_correction_explanation(corrections)

        result = {
            "reading": reading,
            "explanation": explanation,
        }
        return api_response(data=result)

    except ValueError as e:
        return api_response(status="error", error=str(e), code=400)
    except Exception as e:
        return handle_error(e, "Brew Day Correction Error")


@brewday_bp.route("/complete", methods=["POST"])
def complete_session() -> Tuple[Response, int]:
    """
    End the brew day session, generate AI evaluation, and save the log.

    Expects JSON: {"batch_id": str}
    """
    try:
        data = request.json or {}
        batch_id = data.get("batch_id")

        if not batch_id:
            return api_response(status="error", error="Missing batch_id", code=400)

        from services.brewday_coach import BrewSessionManager
        from services.ai import generate_brew_evaluation
        from services.brew_logger import generate_brewday_log

        manager = BrewSessionManager()
        session_summary = manager.end_session(batch_id)

        # Generate AI evaluation
        evaluation = generate_brew_evaluation(session_summary)
        session_summary["evaluation"] = evaluation

        # Save brew day log to disk
        log_path = generate_brewday_log(session_summary)

        result = {
            "session": session_summary,
            "evaluation": evaluation,
            "log_path": log_path,
        }
        return api_response(data=result)

    except ValueError as e:
        return api_response(status="error", error=str(e), code=400)
    except Exception as e:
        return handle_error(e, "Brew Day Complete Error")


@brewday_bp.route("/timers", methods=["GET"])
def get_timers() -> Tuple[Response, int]:
    """
    Get all active timers for a session.

    Query param: ?batch_id=xxx
    """
    try:
        batch_id = request.args.get("batch_id")
        if not batch_id:
            return api_response(status="error", error="Missing batch_id", code=400)

        from services.brewday_coach import BrewSessionManager

        manager = BrewSessionManager()
        timers = manager.get_timers(batch_id)
        return api_response(data={"timers": timers})

    except Exception as e:
        return handle_error(e, "Brew Day Timers Error")
