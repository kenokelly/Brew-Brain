import os
import requests
import numpy as np
from typing import Optional
from datetime import datetime, timezone, timedelta
from core.influx import query_api, INFLUX_BUCKET
from core.cache import cache
from core.config import get_config, logger
from ml.features import query_batch_data, calculate_sg_velocity

# There's no GPU/NPU on this Pi, so every response is slow: measured
# requests (phi3:mini, already warm) took up to 95s for a one-sentence
# prompt, plus ~23s to load the model from the SD card when it isn't
# resident. Every requests.post() timeout below must have real margin over
# that, or the call will always time out and fall back to the canned
# offline message - never a real answer.
#
# All calls share one keep_alive window. They used to mix `keep_alive: 0`
# (unload immediately) with chat's warm window, so any dashboard AI call
# evicted the model and the next chat message paid the reload again. The
# model is ~2.2GB against ~6GB free, so keeping it resident is fine.
OLLAMA_COLD_START_TIMEOUT = 150
OLLAMA_INTERACTIVE_KEEP_ALIVE = "10m"
OLLAMA_KEEP_ALIVE = OLLAMA_INTERACTIVE_KEEP_ALIVE
# Chat runs as a background job, and Ollama serves one request at a time, so
# a message can queue behind another AI call (~2 min) before its own turn.
OLLAMA_CHAT_TIMEOUT = 300
# Cap reply length so one long answer can't hold the Pi's CPU for minutes.
CHAT_MAX_TOKENS = 400
ADVICE_MAX_TOKENS = 200
ADVICE_CACHE_KEY = "ai_proactive_advice"
ADVICE_TTL_S = 3600


# ---------------------------------------------------------------------------
# Provider switch: Claude API ("cloud") or Ollama on the Pi ("local")
# ---------------------------------------------------------------------------

CLOUD_MODELS = ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5")
CLOUD_TIMEOUT_S = 60
# Room for the reply plus any adaptive thinking (Opus/Sonnet think by default)
CLOUD_MAX_TOKENS = 4000


class _LLMResponse:
    """Minimal stand-in for a requests.Response from Ollama's /api/generate,
    so every call site handles cloud and local replies the same way."""

    def __init__(self, data: dict):
        self.status_code = 200
        self._data = data

    def json(self) -> dict:
        return self._data


def cloud_ai_enabled() -> bool:
    return get_config("ai_provider") == "cloud" and bool(get_config("anthropic_api_key"))


def cloud_generate(system: str, prompt: str, api_key: Optional[str] = None,
                   model: Optional[str] = None, max_tokens: int = CLOUD_MAX_TOKENS) -> str:
    """One Claude API call; returns the reply text. Raises on any failure."""
    import anthropic

    model = model or get_config("cloud_model") or CLOUD_MODELS[0]
    if model not in CLOUD_MODELS:
        model = CLOUD_MODELS[0]
    client = anthropic.Anthropic(api_key=api_key or get_config("anthropic_api_key"),
                                 timeout=CLOUD_TIMEOUT_S, max_retries=1)
    kwargs = dict(model=model, max_tokens=max_tokens, system=system or anthropic.NOT_GIVEN,
                  messages=[{"role": "user", "content": prompt}])

    if model == "claude-haiku-4-5":
        # No effort setting on Haiku 4.5; no thinking unless budget_tokens is set
        response = client.messages.create(**kwargs)
    elif model == "claude-opus-5":
        # Chat and advice don't need deep reasoning: low effort keeps replies
        # quick and cheap. Server-side fallback re-runs a declined request on
        # another model instead of failing.
        response = client.beta.messages.create(
            **kwargs, output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
    else:
        response = client.messages.create(**kwargs, output_config={"effort": "low"})

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the request")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise RuntimeError(f"Empty reply (stop_reason={response.stop_reason})")
    return text


def _llm_post(ollama_url: str, payload: dict, timeout: float):
    """Generate via the configured provider. Cloud failures fall back to the
    local Ollama call, so the Brewmaster still answers (slowly) offline."""
    if cloud_ai_enabled():
        try:
            text = cloud_generate(payload.get("system") or "", payload["prompt"])
            return _LLMResponse({"response": text, "source": "cloud"})
        except Exception as e:
            logger.warning(f"Cloud AI failed ({type(e).__name__}: {e}); falling back to local Ollama")
    return requests.post(ollama_url, json=payload, timeout=timeout)


def analyze_yeast_history(yeast_name: str) -> Optional[dict]:
    """
    Queries InfluxDB for historical batches with the same yeast.
    Returns average attenuation, common temp range, and daily drop rate.
    """
    if not yeast_name or yeast_name == "Unknown":
        return None
        
    cache_key = f"yeast_history_{yeast_name}"
    cached = cache.get(cache_key)
    if cached: return cached

    try:
        # 1. Query Daily SG Drop (Rate)
        q_rate = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -365d)
          |> filter(fn: (r) => r["_measurement"] == "calibrated_readings")
          |> filter(fn: (r) => r["yeast"] == "{yeast_name}")
          |> filter(fn: (r) => r["_field"] == "sg")
          |> aggregateWindow(every: 24h, fn: spread, createEmpty: false)
        '''
        res_rate = query_api.query(q_rate)
        drops = []
        for t in res_rate:
            for r in t.records:
                val = r.get_value()
                if val > 0.002: # Only count active fermentation days
                    drops.append(val)
        
        avg_rate = np.mean(drops) if drops else 0.008 # Default 8 points/day
        
        # 2. Query Average Temp
        q_temp = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -365d)
          |> filter(fn: (r) => r["_measurement"] == "calibrated_readings")
          |> filter(fn: (r) => r["yeast"] == "{yeast_name}")
          |> filter(fn: (r) => r["_field"] == "temp")
          |> mean()
        '''
        res_temp = query_api.query(q_temp)
        avg_temp = 20.0
        if res_temp:
            for t in res_temp:
                for r in t.records:
                    avg_temp = r.get_value()

        if not drops:
            return None

        result = {
            "avg_attenuation": 75.0, # Placeholder for complex multi-batch OG/FG calc
            "avg_temp": round(float(avg_temp), 1),
            "avg_rate": round(float(avg_rate), 4),
            "samples": len(drops)
        }

        # Cache result for 4 hours (yeast history doesn't change fast)
        cache.set(cache_key, result, ttl=14400)
        return result

    except Exception as e:
        logger.error(f"AI Yeast History Error: {e}")
        return None

def simulate_brew_insight(yeast_name, brew_count, mean_fg, p95_fg):
    """
    B10: Ask Ollama for insights based on Monte Carlo simulation results.
    Returns null if Ollama fails.
    """
    ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
    ollama_url = f"http://{ollama_host}:11434/api/generate"
    
    prompt = (
        f"We just ran a Monte Carlo simulation for a brew using {yeast_name}. "
        f"Based on {brew_count} historical data points, the median predicted FG is {round(mean_fg, 3)}. "
        f"However, there is a 5% risk of stalling at {round(p95_fg, 3)} or higher. "
        f"Provide a brief, 2-sentence technical recommendation on how to mitigate this stall risk during fermentation."
    )
    
    try:
        payload = {
            "model": get_config("ollama_model") or "llama3:latest",
            "prompt": prompt,
            "system": "You are an expert AI brewmaster assisting with fermentation risk analysis. Keep it under 2 sentences.",
            "stream": False,
            "keep_alive": OLLAMA_KEEP_ALIVE
        }
        res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
        if res.status_code == 200:
            text = res.json().get("response")
            if text:
                return text.strip()
    except Exception as e:
        logger.warning(f"Ollama simulation insight failed: {e}")
    
    return None

_PHASE_TEXT = {
    "LAG": "lag phase (yeast not yet visibly active)",
    "ACTIVE": "active fermentation",
    "SLOWING": "fermentation slowing down",
    "STABLE": "gravity stable (likely finished or nearly finished)",
    "STALLED": "possibly stalled (gravity flat well above target)",
    "RISING": "gravity rising - not a fermentation state; check the hydrometer",
    "NO DATA": "unknown (not enough recent readings)",
}


def _parse_ts(iso: Optional[str]) -> Optional[datetime]:
    try:
        t = datetime.fromisoformat(str(iso))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _ago(iso: str, now: datetime) -> str:
    try:
        mins = (now - datetime.fromisoformat(iso)).total_seconds() / 60
    except (TypeError, ValueError):
        return "recently"
    if mins < 60:
        return f"{int(mins)} min ago"
    if mins < 48 * 60:
        return f"{int(mins / 60)} h ago"
    return f"{int(mins / 1440)} days ago"


def build_batch_context(journal_entries: int = 5) -> str:
    """Plain-text summary of the live batch for AI prompts.

    The AI used to get only a raw SG and an unrounded temperature
    ("22.22222222222222C"), so its answers were generic or invented details.
    This pulls the same numbers the beta dashboard shows - rounded, labelled
    and with units - plus the recipe schedule and recent journal events.
    Kept short: every token costs CPU time on the Pi.
    """
    from services.fermentation import get_fermentation_summary

    now = datetime.now(timezone.utc)
    s = get_fermentation_summary(now)
    lines = []

    if s.get("water_test"):
        # Tilt in plain water to check calibration: fermentation numbers
        # (attenuation, ABV, ETA, steps) are meaningless here.
        cal = s.get("calibration") or {}
        lines.append("WATER TEST MODE: the Tilt hydrometer is floating in plain water to check its calibration. "
                     "No beer is fermenting; fermentation alerts are paused.")
        lines.append("Expected reading in water: 1.000")
        if cal.get("raw_mean") is not None:
            lines.append(f"Raw Tilt reading (last 30 min average): {cal['raw_mean']:.3f}, spread {cal.get('spread', 0):.3f}; "
                         f"current offset {cal.get('current_offset', 0):+.3f}")
        if cal.get("message"):
            lines.append(f"Calibration status: {cal['message']}")
        if s.get("temp") is not None:
            lines.append(f"Water temperature {s['temp']:.1f}°C")
        return "\n".join(lines)

    recipe = ", ".join(x for x in (s.get("style"), f"yeast {s.get('yeast')}" if s.get("yeast") else None)
                       if x and "Unknown" not in str(x))
    lines.append(f"Batch: {s.get('batch_name') or 'unnamed'}" + (f" ({recipe})" if recipe else ""))
    if s.get("day"):
        lines.append(f"Day {s['day']} since pitch")
    lines.append(f"Original gravity {s['og']:.3f}, target final gravity {s['target_fg']:.3f}")

    sg = s.get("sg")
    if sg is not None:
        line = f"Current gravity {sg:.3f}"
        if s.get("attenuation") is not None:
            line += f" ({s['attenuation']:.0f}% attenuation, about {s.get('abv') or 0:.1f}% ABV so far)"
        lines.append(line)
    else:
        lines.append("Current gravity: no reading")

    v = s.get("velocity")
    if v is not None:
        if v <= -0.2:
            lines.append(f"Gravity falling {-v:.1f} points/day over the last 24 h")
        elif v >= 0.2:
            lines.append(f"Gravity RISING {v:.1f} points/day over the last 24 h (unusual: hydrometer moved or misreading?)")
        else:
            lines.append("Gravity flat over the last 24 h")
    lines.append(f"Fermentation state: {_PHASE_TEXT.get(s.get('phase'), s.get('phase'))}")
    eta = s.get("eta_days")
    if eta == 0:
        lines.append("Gravity is at or below the target final gravity")
    elif eta is not None:
        lines.append(f"Estimated {eta:.1f} days to target final gravity at the current rate")

    temp = s.get("temp")
    if temp is not None:
        line = f"Beer temperature {temp:.1f}°C"
        if s.get("target_temp") is not None:
            line += f" (target {s['target_temp']:.1f}°C, {s.get('temp_delta') or 0:+.1f}°C off)"
        lines.append(line)

    sched = s.get("schedule") or {}
    cur, nxt = sched.get("current"), sched.get("next")
    if cur:
        line = f"Recipe step {sched['current_index'] + 1} of {len(sched['steps'])}: {cur['name']}"
        if cur.get("temp") is not None:
            line += f" at {cur['temp']:g}°C"
        lines.append(line)
    if nxt:
        days = sched.get("days_to_next")
        when = f"in {days * 24:.0f} h" if days is not None and days < 1 else f"in {days:.1f} days" if days is not None else ""
        lines.append(f"Next step: {nxt['name']}" + (f" at {nxt['temp']:g}°C" if nxt.get("temp") is not None else "") + f" {when}".rstrip())
    elif sched and sched.get("current_index", 0) >= len(sched.get("steps", [])):
        lines.append("Fermentation schedule complete; ready to package")

    age = (s.get("sensor") or {}).get("last_reading_age_min")
    if age is None or age > 60:
        lines.append("WARNING: no hydrometer reading in the last hour; data may be stale")
    if s.get("test_mode"):
        lines.append("NOTE: test mode is on; readings are simulated")
    if not s.get("brew_active"):
        lines.append("NOTE: Brew Active is off (no batch is being actively monitored)")

    try:
        from services.journal import list_entries
        # Collapse repeats (an alert re-firing with slightly different
        # numbers) so the AI sees distinct events
        import re
        from services.fermentation import _log_start
        since = _log_start()
        recent, seen = [], set()
        for e in list_entries(journal_entries * 6):
            # Events from before the log start are a water test or the last batch
            if since and _parse_ts(e.get("ts")) and _parse_ts(e["ts"]) < since:
                continue
            key = re.sub(r"[-+]?\d[\d.]*", "#", e["text"])[:80]
            if key not in seen:
                seen.add(key)
                recent.append(e)
            if len(recent) == journal_entries:
                break
    except Exception:
        recent = []
    if recent:
        lines.append("Recent events (newest first):")
        lines.extend(f"- {_ago(e['ts'], now)}: {e['text'][:140]}" for e in recent)

    return "\n".join(lines)


# What the chat should know about Brew Brain itself, so "how do I..." questions
# get real answers instead of "I can't see your system".
APP_GUIDE = (
    "You are built into Brew Brain, the user's fermentation monitor (Raspberry Pi, Tilt hydrometer, "
    "Brewfather). The dashboard's Proactive Advice card, the alerts and the journal events below all come "
    "from Brew Brain, i.e. from you; if the user quotes them, explain them against the live data and say "
    "plainly if one was wrong. How the app works:\n"
    "- Settings > System Control > Brew Alerts slider (called "Brew Active" before 18 Oct 2026): turns Tilt alerts (signal loss, stall, runaway, "
    "temperature) on or off. Simulated Data slider: fake readings for testing; keep it off during a brew.\n"
    "- Dashboard: Sync from Brewfather loads the fermenting batch, recipe OG/FG and fermentation steps. "
    "Water test button: calibrate the Tilt in plain water (alerts pause). "
    "Fermentation chart > Start log from now: hides earlier readings such as a water test.\n"
    "- Settings > Tilt offset corrects calibration (add the difference between a trusted reading and the Tilt).\n"
    "- Telegram bot: alerts, a daily report, and /status, /ping, /help commands.\n"
    "- The TiltPi / Node-RED panel shows the raw Tilt data."
)


def generate_chat_response(message: str, history: Optional[list] = None) -> dict:
    """
    Generates a response from the Brewmaster AI (Local Ollama).
    """
    try:
        try:
            context = build_batch_context()
        except Exception as ctx_e:
            logger.warning(f"Batch context unavailable for chat: {ctx_e}")
            context = "Live batch data is currently unavailable."

        plan = _batch_plan()
        system_prompt = (
            "You are the 'Brewmaster', an expert homebrewing assistant. "
            f"{APP_GUIDE}\n\n"
            "Here is the live data for the user's current batch:\n"
            f"{context}\n"
            + (f"Brewer's fermentation plan: {plan}\n" if plan else "") + "\n"
            "Base your answer on these numbers and quote them where useful. "
            "Don't invent readings, dates or ingredients that aren't listed. "
            "If the data looks implausible (for example gravity below 1.000, or rising), "
            "say so and suggest checking the hydrometer. Don't contradict the recipe schedule or the "
            "brewer's plan. Be concise and practical."
        )

        # 1. Try Local Ollama
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        prompt = message
        if history:
            # Simple history flattening
            try:
                history_str = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" if isinstance(m, dict) else str(m) for m in history])
                prompt = f"Context of previous messages:\n{history_str}\n\nUser: {message}"
            except Exception as hist_e:
                logger.warning(f"Failed to parse history: {hist_e}")

        payload = {
            "model": get_config("ollama_model") or "llama3:latest",
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "keep_alive": OLLAMA_INTERACTIVE_KEEP_ALIVE,
            "options": {"num_predict": CHAT_MAX_TOKENS},
        }

        try:
            logger.info(f"Sending request to Ollama ({ollama_url}) with model {payload.get('model')}")
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_CHAT_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "response": text.strip(), "source": res.json().get("source", "ollama")}
        except Exception as e:
            logger.error(f"Ollama chat failed at {ollama_url}: {e}")

        return {
            "status": "fallback", 
            "response": "The Brewmaster is currently offline, so I can't give detailed advice right now. Here's your batch as it stands:\n" + context,
            "source": "template"
        }

    except Exception as e:
        logger.error(f"Chat AI Error: {e}")
        return {"status": "error", "message": str(e)}

def _fixed_advice() -> Optional[dict]:
    """Advice that shouldn't come from the AI: simulated data or a water test."""
    if get_config("test_mode"):
        return {"status": "success", "source": "template",
                "advice": "Simulated data is on, so there's no real batch to advise on. "
                          "Turn off Simulated Data in Settings to get advice on your Tilt readings."}
    if get_config("water_test"):
        return {"status": "success", "source": "template",
                "advice": "Water test running: the Tilt should read 1.000 in plain water. "
                          "Use the water test card to check and apply the offset, then end the test "
                          "before the Tilt goes into the fermenter."}
    return None


def _batch_plan(max_chars: int = 500) -> str:
    """The fermentation part of the batch notes (temperatures, dry hop, crash), if any."""
    import re
    notes = (get_config("batch_notes") or "").strip()
    if not notes:
        return ""
    m = re.search(r"Fermentation:(.+?)(?:(?<=\.)\s+[A-Z][a-z]+:|$)", notes, re.S)
    plan = (m.group(1) if m else notes).strip()
    return plan[:max_chars]


def _plain_text(text: str) -> str:
    """Drop markdown headers, bullets and stray emphasis; keep **bold** (the card renders it)."""
    import re
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+)(?<!\*)\*(?!\*)", r"\1", text)
    return text.strip()


def get_proactive_advice(refresh: bool = False) -> dict:
    """
    Proactive advice for the dashboard, cached for an hour.

    The dashboard's advice card requested this on every page view, and each
    generation holds the Pi's CPU for ~2 minutes. Ollama serves one request
    at a time, so a chat message sent right after opening the dashboard
    queued behind it and timed out. Serve the cached answer; generate at most
    one at a time (a Redis lock) and only when the cache has expired.
    """
    fixed = _fixed_advice()
    if fixed:
        return fixed
    cached = None if refresh else cache.get(ADVICE_CACHE_KEY)
    if cached:
        return cached
    lock = cache.redis_client.set(f"{ADVICE_CACHE_KEY}_lock", "1", nx=True, ex=OLLAMA_COLD_START_TIMEOUT + 30) \
        if cache.redis_client else True
    if not lock:
        return {
            "status": "fallback",
            "advice": "The Brewmaster is thinking about your batch. Check back in a couple of minutes.",
            "source": "pending",
        }
    try:
        result = _generate_proactive_advice()
        if result.get("status") == "success":
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            cache.set(ADVICE_CACHE_KEY, result, ttl=ADVICE_TTL_S)
        return result
    finally:
        if cache.redis_client:
            cache.redis_client.delete(f"{ADVICE_CACHE_KEY}_lock")


def _generate_proactive_advice() -> dict:
    """
    Analyzes current fermentation and provides proactive advice using AI.
    """
    try:
        from services.yeast import search_yeast_meta

        # Same live summary the chat uses (step timeline, velocity, ETA,
        # journal). The yeast was read from a "yeast_name" key that doesn't
        # exist, so advice always said "Unknown" yeast; it's yeast_strain.
        context = build_batch_context(journal_entries=3)
        yeast_name = get_config("yeast_strain") or "Unknown"
        yeast_specs = search_yeast_meta(yeast_name) if yeast_name != "Unknown" else {}

        system_prompt = (
            "You are the 'Brewmaster', an expert in fermentation management. "
            "Give proactive advice for the next 24-48 hours of this batch: what to do now and what's coming "
            "(diacetyl rest, dry hop, cold crash) and anything in the data that needs attention. "
            "Rules: use only the numbers given and quote them; don't invent readings, gravity targets or dates. "
            "Follow the recipe schedule and the brewer's plan exactly; never suggest temperatures or timings "
            "that contradict them. If the data looks wrong, say what to check. "
            "Plain text, no headings or lists, at most 3 short sentences."
        )

        context_parts = [context]
        plan = _batch_plan()
        if plan:
            context_parts.append(f"Brewer's fermentation plan: {plan}")
        if yeast_specs and "error" not in yeast_specs:
            # Only include key specs to save context tokens/RAM
            context_parts.append(f"Yeast specs: {yeast_specs.get('attenuation')}, {yeast_specs.get('temp_range')}")

        prompt = "\n".join(context_parts) + "\n\nProvide specific proactive recommendations for the next 24-48 hours."

        # 2. Call Ollama
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE,
                "options": {"num_predict": ADVICE_MAX_TOKENS},
            }
            logger.info("Sending proactive advice request to Ollama")
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "advice": _plain_text(text), "source": res.json().get("source", "ollama")}
        except Exception as e:
            logger.error(f"Ollama proactive advice failed at {ollama_url}: {e}")

        # Fallback advice
        return {
            "status": "fallback",
            "advice": "Ensure temperature remains stable. If gravity has dropped by 75%, consider a diacetyl rest by raising the temperature by 2-3°C.",
            "source": "template"
        }

    except Exception as e:
        logger.error(f"Proactive Advice AI Error: {e}")
        return {"status": "error", "message": str(e)}

def analyze_anomaly(anomaly_data: dict) -> dict:
    """
    Uses the Brewmaster AI to analyze a fermentation anomaly and provide advice.
    """
    try:
        anomaly_type = anomaly_data.get("type", "Unknown Anomaly")
        severity = anomaly_data.get("severity", "warning")
        message = anomaly_data.get("message", "No description available")
        batch_name = anomaly_data.get("batch_name", "the current batch")
        
        system_prompt = (
            "You are the 'Brewmaster', an expert in fermentation troubleshooting. "
            "Analyze the following anomaly and provide a technical yet accessible explanation and 2-3 actionable steps. "
            "Be concise and professional."
        )
        
        prompt = (
            f"Anomaly Type: {anomaly_type}\n"
            f"Severity: {severity}\n"
            f"Description: {message}\n"
            f"Batch: {batch_name}\n\n"
            "Please provide an analysis and recommendations."
        )

        # Try Local Ollama
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE
            }
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "analysis": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.error(f"Ollama anomaly analysis failed at {ollama_url}: {e}")

        return {
            "status": "fallback",
            "analysis": f"The Brewmaster suggests checking the {anomaly_type} carefully. Ensure your Tilt is calibrated and temperature is stable.",
            "source": "template"
        }

    except Exception as e:
        logger.error(f"Anomaly AI Error: {e}")
        return {"status": "error", "message": str(e)}

def predict_issues() -> Optional[str]:
    """
    Analyzes recent trends and uses AI to predict impending issues.
    Returns a warning message if an issue is predicted, else None.
    """
    try:
        from services.status import get_status_dict
        from ml.features import query_batch_data, calculate_sg_velocity
        
        status = get_status_dict() or {}
        raw_sg = status.get("sg")
        try:
            sg = float(raw_sg) if raw_sg is not None else 1.050
        except (ValueError, TypeError):
            sg = 1.050

        raw_target_fg = get_config("target_fg")
        try:
            target_fg = float(raw_target_fg) if raw_target_fg is not None else 1.010
        except (ValueError, TypeError):
            target_fg = 1.010
        
        # 1. Check if we are in a 'stall-risk' zone
        if sg <= target_fg + 0.002:
            return None # Fermentation essentially complete

            
        # 2. Get Velocity Trend (Last 48h vs Last 12h)
        now = datetime.now(timezone.utc)
        data_12h = query_batch_data(now - timedelta(hours=12), now)
        data_48h = query_batch_data(now - timedelta(hours=48), now)
        
        vel_12h = calculate_sg_velocity(data_12h["sg_readings"], data_12h["sg_times"]) if data_12h["sg_readings"] else 0.0
        vel_48h = calculate_sg_velocity(data_48h["sg_readings"], data_48h["sg_times"]) if data_48h["sg_readings"] else 0.0
        
        # 3. AI Analysis if trend is negative (slowing down significantly)
        if vel_12h < (vel_48h * 0.4) and vel_48h > 2.0:
            system_prompt = "You are the 'Brewmaster'. Analyze fermentation speed and flag risks of a stall."
            prompt = (
                f"Current SG: {sg}\nTarget FG: {target_fg}\n"
                f"Velocity (48h avg): {vel_48h} pts/day\n"
                f"Velocity (Last 12h): {vel_12h} pts/day\n\n"
                "Is this a normal slowdown or a risk of a premature stall? "
                "Provide a 1-sentence warning if risky, else respond 'Normal'."
            )
            
            ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
            ollama_url = f"http://{ollama_host}:11434/api/generate"
            
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE
            }
            
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                answer = res.json().get("response", "").strip()
                if "Normal" not in answer:
                    return f"🤖 *AI PREDICTION:* {answer}"
                    
        return None
    except Exception as e:
        logger.error(f"AI Predictive Issue Error: {e}")
        return None

def generate_narrative(batch_data: dict) -> dict:
    """
    Generates a human-readable narrative summary of a batch's progress.
    """
    try:
        name = batch_data.get("name", "Unknown")
        style = batch_data.get("style", "Beer")
        og = batch_data.get("og", 1.050)
        fg = batch_data.get("fg", 1.010)
        temp_avg = batch_data.get("temp_avg", 20.0)
        status = batch_data.get("status", "unknown")

        prompt = (
            f"Summarize the following fermentation batch:\n"
            f"Batch Name: {name}\n"
            f"Style: {style}\n"
            f"OG: {og}\n"
            f"Current SG: {fg}\n"
            f"Average Temp: {temp_avg}C\n"
            f"Status: {status}\n\n"
            "Provide a short (2-sentence) professional narrative for a head brewer."
        )

        # 1. Try Local Ollama (Edge AI)
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE
            }
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "narrative": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.error(f"Ollama not available at {ollama_url}. Error: {e}")

        # 2. Fallback to Template
        return {
            "status": "fallback",
            "narrative": f"Batch '{name}' is currently {status}. It started at {og} and is now at {fg}, holding an average temperature of {temp_avg}C.",
            "source": "template"
        }

    except Exception as e:
        logger.error(f"Narrative AI Error: {e}")
        return {"status": "error", "message": str(e)}


def generate_brewday_coaching_response(context: dict, message: str) -> dict:
    """
    Generate an AI coaching response during an active brew day session.

    Uses a brew-day-specific system prompt and keeps the model warm in RAM
    (keep_alive: "30m") because the brewer will send multiple messages during
    a session.

    Args:
        context: Session context dict containing phase, recipe, telemetry, etc.
        message: The brewer's question or chat message.

    Returns:
        Response dict with status, response text, and source.
    """
    try:
        phase = context.get("phase", "unknown")
        batch_name = context.get("batch_name", "current batch")
        recipe = context.get("recipe", {})
        gravity_readings = context.get("gravity_readings", [])
        corrections = context.get("corrections_applied", [])

        # Build a rich system prompt with session awareness
        system_prompt = (
            "You are the 'Brew Day Coach', an expert AI assistant guiding a homebrewer "
            "through their brew day in real time. You have full access to the recipe and "
            "live session data.\n\n"
            f"Current batch: {batch_name}\n"
            f"Current phase: {phase}\n"
            f"Recipe OG: {recipe.get('og', 'N/A')}\n"
            f"Recipe style: {recipe.get('style', 'N/A')}\n"
            f"Gravity readings so far: {len(gravity_readings)}\n"
            f"Corrections applied: {len(corrections)}\n\n"
            "Be concise, technical, and actionable. Tailor advice to the current phase. "
            "If the brewer asks about timing, temperatures, or corrections, use the "
            "session data to give specific numbers."
        )

        # Inject recent gravity readings for context
        if gravity_readings:
            latest = gravity_readings[-1]
            system_prompt += (
                f"\nLatest gravity reading: {latest.get('sg', 'N/A')} "
                f"at {latest.get('volume_l', 'N/A')}L ({latest.get('stage', 'N/A')})"
            )

        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"

        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": message,
                "system": system_prompt,
                "stream": False,
                "keep_alive": "30m",
            }
            logger.info(f"Brew Day Coach request to Ollama ({phase} phase)")
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "response": text.strip(), "source": res.json().get("source", "ollama")}
        except Exception as e:
            logger.error(f"Ollama brew day coaching failed: {e}")

        # Fallback
        return {
            "status": "fallback",
            "response": (
                f"The Brew Day Coach is currently offline. "
                f"You are in the '{phase}' phase of {batch_name}. "
                f"Refer to your recipe for guidance on the next steps."
            ),
            "source": "template",
        }

    except Exception as e:
        logger.error(f"Brew Day Coaching AI Error: {e}")
        return {"status": "error", "message": str(e)}


def generate_correction_explanation(correction_data: dict) -> dict:
    """
    Ask the LLM to explain pre-computed correction math in plain language.

    The math has already been computed by brew_math.py — this function only
    generates a human-friendly explanation of what the numbers mean and the
    trade-offs of each option.

    Args:
        correction_data: Dict with keys like dme_addition_g, dilution_water_l,
                         boil_extension_min, measured_sg, target_sg, stage.

    Returns:
        Response dict with status, explanation text, and source.
    """
    try:
        measured = correction_data.get("measured_sg", "N/A")
        target = correction_data.get("target_sg", "N/A")
        stage = correction_data.get("stage", "unknown")

        # Build a structured prompt from the correction values
        correction_lines = [
            f"Stage: {stage}",
            f"Measured SG: {measured}",
            f"Target SG: {target}",
        ]
        if "dme_addition_g" in correction_data:
            correction_lines.append(f"DME addition needed: {correction_data['dme_addition_g']}g")
        if "boil_extension_min" in correction_data:
            correction_lines.append(f"Extended boil needed: {correction_data['boil_extension_min']} minutes")
        if "dilution_water_l" in correction_data:
            correction_lines.append(f"Dilution water needed: {correction_data['dilution_water_l']}L")

        prompt = (
            "The following gravity corrections have been calculated for a brew day:\n\n"
            + "\n".join(correction_lines)
            + "\n\nExplain these corrections to a homebrewer in 3-4 sentences. "
            "Cover the impact on the final beer (ABV, body, flavour) and recommend "
            "which correction option is best for this situation."
        )

        system_prompt = (
            "You are the 'Brew Day Coach', an expert brewing advisor. "
            "Explain gravity corrections clearly and concisely. "
            "Do NOT recalculate the math — the numbers are already correct. "
            "Focus on practical impact and recommendations."
        )

        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"

        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "keep_alive": "30m",
            }
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "explanation": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.error(f"Ollama correction explanation failed: {e}")

        # Fallback: template-based explanation
        parts = [f"Your gravity is {measured} but the target is {target}."]
        if "dme_addition_g" in correction_data:
            parts.append(
                f"Adding {correction_data['dme_addition_g']}g of DME will raise the gravity to target."
            )
        if "dilution_water_l" in correction_data:
            parts.append(
                f"Adding {correction_data['dilution_water_l']}L of water will dilute to target."
            )
        if "boil_extension_min" in correction_data:
            parts.append(
                f"Extending the boil by {correction_data['boil_extension_min']} minutes will concentrate the wort."
            )

        return {
            "status": "fallback",
            "explanation": " ".join(parts),
            "source": "template",
        }

    except Exception as e:
        logger.error(f"Correction Explanation AI Error: {e}")
        return {"status": "error", "message": str(e)}


def generate_brew_evaluation(session_summary: dict) -> dict:
    """
    Generate an end-of-session AI evaluation of the brew day.

    Analyses gravity readings, corrections, phase timings, and events to
    produce a quality assessment. Uses the shared keep_alive window so it doesn't evict the model
    immediately after generation (session is over).

    Args:
        session_summary: Full session dict from BrewSessionManager.end_session().

    Returns:
        Response dict with status, evaluation text, and source.
    """
    try:
        batch_name = session_summary.get("batch_name", "Unknown")
        recipe = session_summary.get("recipe", {})
        readings = session_summary.get("gravity_readings", [])
        corrections = session_summary.get("corrections_applied", [])
        events = session_summary.get("events", [])
        started_at = session_summary.get("started_at", "N/A")
        ended_at = session_summary.get("ended_at", "N/A")

        prompt = (
            f"Evaluate this brew day session:\n\n"
            f"Batch: {batch_name}\n"
            f"Recipe style: {recipe.get('style', 'N/A')}\n"
            f"Target OG: {recipe.get('og', 'N/A')}\n"
            f"Session start: {started_at}\n"
            f"Session end: {ended_at}\n"
            f"Total gravity readings: {len(readings)}\n"
            f"Corrections applied: {len(corrections)}\n"
            f"Total events: {len(events)}\n"
        )

        if readings:
            prompt += "\nGravity readings:\n"
            for r in readings:
                prompt += f"  - {r.get('stage', '?')}: {r.get('sg', '?')} @ {r.get('volume_l', '?')}L\n"

        if corrections:
            prompt += "\nCorrections applied:\n"
            for c in corrections:
                prompt += f"  - Stage {c.get('stage', '?')}: measured {c.get('measured_sg', '?')}, target {c.get('target_sg', '?')}\n"

        prompt += (
            "\nProvide a brief brew day evaluation (4-5 sentences). "
            "Score the session out of 10. Note what went well and what to "
            "improve next time. Be encouraging but honest."
        )

        system_prompt = (
            "You are the 'Brew Day Coach', providing an end-of-session evaluation. "
            "Be constructive, specific, and reference the actual data provided."
        )

        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"

        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE,
            }
            logger.info(f"Generating brew day evaluation for {batch_name}")
            res = _llm_post(ollama_url, payload, timeout=OLLAMA_COLD_START_TIMEOUT)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "evaluation": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.error(f"Ollama brew evaluation failed: {e}")

        # Fallback evaluation
        reading_count = len(readings)
        correction_count = len(corrections)
        return {
            "status": "fallback",
            "evaluation": (
                f"Brew day for '{batch_name}' is complete. "
                f"You recorded {reading_count} gravity reading(s) and applied "
                f"{correction_count} correction(s). "
                f"Review your readings against the recipe targets to assess efficiency. "
                f"The Brew Day Coach AI is currently offline for a detailed evaluation."
            ),
            "source": "template",
        }

    except Exception as e:
        logger.error(f"Brew Evaluation AI Error: {e}")
        return {"status": "error", "message": str(e)}
