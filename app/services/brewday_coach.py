"""
Brew Day Session Manager — Redis-backed state machine for brew day coaching.

Manages brew day sessions through defined phases, records gravity readings,
computes corrections via brew_math, and tracks timers and events.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from core.cache import cache
from core.config import logger
from services.brew_math import (
    calculate_dme_addition,
    calculate_dilution_water,
    calculate_boil_extension,
)


class BrewSessionManager:
    """State machine for a single brew day session, persisted in Redis."""

    PHASES: List[str] = [
        "setup",
        "strike",
        "mash",
        "sparge",
        "boil",
        "knockout",
        "complete",
    ]
    SESSION_TTL: int = 86400  # 24 hours

    # --- Redis key helpers ---

    @staticmethod
    def _session_key(batch_id: str) -> str:
        return f"brewday:session:{batch_id}"

    @staticmethod
    def _events_key(batch_id: str) -> str:
        return f"brewday:events:{batch_id}"

    @staticmethod
    def _timers_key(batch_id: str) -> str:
        return f"brewday:timers:{batch_id}"

    # --- Core lifecycle ---

    def start_session(self, batch_id: str, recipe_data: dict) -> dict:
        """
        Initialise a new brew day session for the given batch.

        Args:
            batch_id: Unique batch identifier.
            recipe_data: Recipe dict (name, OG, FG, boil_time, etc.).

        Returns:
            The initial session state dict.
        """
        now = datetime.now(timezone.utc).isoformat()

        session: Dict[str, Any] = {
            "batch_id": batch_id,
            "batch_name": recipe_data.get("name", f"Batch {batch_id}"),
            "recipe": recipe_data,
            "phase": self.PHASES[0],
            "phase_index": 0,
            "started_at": now,
            "phase_started_at": now,
            "gravity_readings": [],
            "corrections_applied": [],
        }

        cache.set(self._session_key(batch_id), session, ttl=self.SESSION_TTL)

        # Initialise empty timers list
        cache.set(self._timers_key(batch_id), [], ttl=self.SESSION_TTL)

        # Record the session-start event
        self._push_event(batch_id, "session_started", {"recipe": recipe_data.get("name", batch_id)})

        logger.info(f"Brew day session started: batch_id={batch_id}")
        return session

    def get_current_state(self, batch_id: str) -> Optional[dict]:
        """Return the current session state, or None if no active session."""
        return cache.get(self._session_key(batch_id))

    def advance_step(self, batch_id: str) -> dict:
        """
        Advance the session to the next phase.

        Returns:
            Updated session state dict.

        Raises:
            ValueError: If no active session or already complete.
        """
        session = self._require_session(batch_id)

        current_index: int = session["phase_index"]
        if current_index >= len(self.PHASES) - 1:
            raise ValueError("Session is already in the final phase (complete)")

        next_index = current_index + 1
        now = datetime.now(timezone.utc).isoformat()

        old_phase = session["phase"]
        session["phase_index"] = next_index
        session["phase"] = self.PHASES[next_index]
        session["phase_started_at"] = now

        cache.set(self._session_key(batch_id), session, ttl=self.SESSION_TTL)

        self._push_event(
            batch_id,
            "phase_advanced",
            {"from": old_phase, "to": session["phase"]},
        )

        logger.info(f"Brew day phase advanced: {old_phase} -> {session['phase']} (batch {batch_id})")
        return session

    def record_event(self, batch_id: str, event_type: str, data: dict) -> None:
        """
        Append a timestamped event to the session event log.

        Args:
            batch_id: Batch identifier.
            event_type: Short event type string (e.g. 'note', 'hop_addition').
            data: Arbitrary event payload.
        """
        self._push_event(batch_id, event_type, data)

    def add_timer(
        self, batch_id: str, name: str, duration_min: int, addition_type: str
    ) -> dict:
        """
        Add a brew-day timer (e.g. hop addition, mash rest).

        Args:
            batch_id: Batch identifier.
            name: Human-readable timer name.
            duration_min: Duration in minutes.
            addition_type: Category (e.g. 'hop', 'mash_rest', 'whirlpool').

        Returns:
            The timer dict that was created.
        """
        self._require_session(batch_id)

        now = datetime.now(timezone.utc).isoformat()
        timer: Dict[str, Any] = {
            "name": name,
            "duration_min": duration_min,
            "addition_type": addition_type,
            "started_at": now,
        }

        timers = cache.get(self._timers_key(batch_id)) or []
        timers.append(timer)
        cache.set(self._timers_key(batch_id), timers, ttl=self.SESSION_TTL)

        self._push_event(
            batch_id,
            "timer_added",
            {"name": name, "duration_min": duration_min, "type": addition_type},
        )

        logger.info(f"Timer added: {name} ({duration_min}min) for batch {batch_id}")
        return timer

    def get_timers(self, batch_id: str) -> list:
        """Return all timers for the session."""
        return cache.get(self._timers_key(batch_id)) or []

    def record_gravity_reading(
        self, batch_id: str, sg: float, volume_l: float, stage: str
    ) -> dict:
        """
        Record a gravity reading and compute corrections against recipe targets.

        Args:
            batch_id: Batch identifier.
            sg: Measured specific gravity.
            volume_l: Current wort volume in litres.
            stage: Brew day stage (e.g. 'pre_boil', 'post_boil', 'mash').

        Returns:
            Dict with the reading, any corrections, and context.
        """
        session = self._require_session(batch_id)
        recipe = session.get("recipe", {})

        now = datetime.now(timezone.utc).isoformat()

        reading: Dict[str, Any] = {
            "sg": sg,
            "volume_l": volume_l,
            "stage": stage,
            "timestamp": now,
        }

        # Determine the target gravity for this stage
        target_sg = self._target_sg_for_stage(recipe, stage)

        corrections: Dict[str, Any] = {}
        if target_sg is not None and sg > 1.0:
            if sg < target_sg:
                # Under-gravity: compute DME addition and boil extension
                try:
                    dme_grams = calculate_dme_addition(sg, target_sg, volume_l)
                    corrections["dme_addition_g"] = round(dme_grams, 1)
                except ValueError:
                    pass

                boil_off_rate = float(recipe.get("boil_off_rate_lpm", 0.05))
                if boil_off_rate > 0:
                    try:
                        extra_min = calculate_boil_extension(
                            sg, target_sg, volume_l, boil_off_rate
                        )
                        corrections["boil_extension_min"] = round(extra_min, 1)
                    except ValueError:
                        pass

            elif sg > target_sg:
                # Over-gravity: compute dilution water
                try:
                    water_l = calculate_dilution_water(sg, target_sg, volume_l)
                    corrections["dilution_water_l"] = round(water_l, 2)
                except ValueError:
                    pass

        if corrections:
            corrections["measured_sg"] = sg
            corrections["target_sg"] = target_sg
            corrections["stage"] = stage
            corrections["timestamp"] = now

        reading["corrections"] = corrections

        # Persist to session
        session["gravity_readings"].append(reading)
        if corrections:
            session["corrections_applied"].append(corrections)
        cache.set(self._session_key(batch_id), session, ttl=self.SESSION_TTL)

        self._push_event(batch_id, "gravity_reading", reading)

        logger.info(
            f"Gravity reading recorded: {sg} @ {volume_l}L ({stage}) for batch {batch_id}"
        )
        return reading

    def end_session(self, batch_id: str) -> dict:
        """
        End the brew day session and return a full summary.

        Returns:
            Session summary dict including all events.
        """
        session = self._require_session(batch_id)

        now = datetime.now(timezone.utc).isoformat()
        session["phase"] = "complete"
        session["phase_index"] = len(self.PHASES) - 1
        session["ended_at"] = now

        # Gather all events
        events = self._get_all_events(batch_id)
        session["events"] = events

        # Gather timers
        session["timers"] = self.get_timers(batch_id)

        # Persist final state before cleanup
        cache.set(self._session_key(batch_id), session, ttl=self.SESSION_TTL)

        self._push_event(batch_id, "session_ended", {"ended_at": now})

        logger.info(f"Brew day session ended: batch_id={batch_id}")
        return session

    # --- Private helpers ---

    def _require_session(self, batch_id: str) -> dict:
        """Load session or raise ValueError."""
        session = self.get_current_state(batch_id)
        if session is None:
            raise ValueError(f"No active brew day session for batch_id={batch_id}")
        return session

    def _push_event(self, batch_id: str, event_type: str, data: dict) -> None:
        """Append a JSON-encoded event to the Redis list for the session."""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        event_json = json.dumps(event)

        if cache.redis_client:
            try:
                cache.redis_client.rpush(self._events_key(batch_id), event_json)
                cache.redis_client.expire(self._events_key(batch_id), self.SESSION_TTL)
                return
            except Exception as e:
                logger.error(f"Redis RPUSH error for events: {e}")

        # Fallback: store events in the session dict itself
        session = cache.get(self._session_key(batch_id))
        if session:
            fallback_events = session.get("_fallback_events", [])
            fallback_events.append(event)
            session["_fallback_events"] = fallback_events
            cache.set(self._session_key(batch_id), session, ttl=self.SESSION_TTL)

    def _get_all_events(self, batch_id: str) -> List[dict]:
        """Retrieve all events for a session."""
        if cache.redis_client:
            try:
                raw_events = cache.redis_client.lrange(
                    self._events_key(batch_id), 0, -1
                )
                return [json.loads(e) for e in raw_events]
            except Exception as e:
                logger.error(f"Redis LRANGE error for events: {e}")

        # Fallback
        session = cache.get(self._session_key(batch_id))
        if session:
            return session.get("_fallback_events", [])
        return []

    @staticmethod
    def _target_sg_for_stage(recipe: dict, stage: str) -> Optional[float]:
        """
        Determine the target SG for a given brew-day stage from the recipe.

        Looks for explicit stage-keyed targets first, then falls back to OG.
        """
        # Explicit stage targets (e.g. recipe might set pre_boil_sg, post_boil_sg)
        stage_key = f"{stage}_sg"
        if stage_key in recipe:
            try:
                return float(recipe[stage_key])
            except (ValueError, TypeError):
                pass

        # Fall back to recipe OG for post-boil / general readings
        og = recipe.get("og") or recipe.get("OG")
        if og is not None:
            try:
                return float(og)
            except (ValueError, TypeError):
                pass

        return None
