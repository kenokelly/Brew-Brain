import os
import requests
import numpy as np
from typing import Optional
from datetime import datetime, timezone, timedelta
from core.influx import query_api, INFLUX_BUCKET
from core.cache import cache
from core.config import get_config, logger

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
            "keep_alive": 0
        }
        res = requests.post(ollama_url, json=payload, timeout=60)
        if res.status_code == 200:
            text = res.json().get("response")
            if text:
                return text.strip()
    except Exception as e:
        logger.warning(f"Ollama simulation insight failed: {e}")
    
    return None

def generate_chat_response(message: str, history: Optional[list] = None) -> dict:
    """
    Generates a response from the Brewmaster AI (Local Ollama).
    """
    try:
        from services.status import get_status_dict
        status = get_status_dict()
        sg = status.get("sg", "N/A")
        temp = status.get("temp", "N/A")
        
        system_prompt = (
            "You are the 'Brewmaster', a helpful and expert AI assistant for homebrewers. "
            "You have access to real-time fermentation data. "
            "The user's current batch is at " + str(sg) + " SG and " + str(temp) + "C. "
            "Be professional, encouraging, and highly technical when appropriate."
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
            "keep_alive": 0
        }

        try:
            logger.info(f"Sending request to Ollama ({ollama_url}) with model {payload.get('model')}")
            res = requests.post(ollama_url, json=payload, timeout=15)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "response": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.error(f"Ollama chat failed at {ollama_url}: {e}")

        return {
            "status": "fallback", 
            "response": "The Brewmaster is currently offline. I can see your batch is at " + str(sg) + " SG, but I can't provide detailed advice right now.",
            "source": "template"
        }

    except Exception as e:
        logger.error(f"Chat AI Error: {e}")
        return {"status": "error", "message": str(e)}

def get_proactive_advice() -> dict:
    """
    Analyzes current fermentation and provides proactive advice using AI.
    """
    try:
        from services.status import get_status_dict
        from services.yeast import search_yeast_meta
        from ml.features import query_batch_data, calculate_sg_velocity
        
        status = get_status_dict()
        batch_name = status.get("batch_name", "the current batch")
        yeast_name = get_config("yeast_name") or "Unknown"
        sg = status.get("sg", "N/A")
        temp = status.get("temp", "N/A")
        og = status.get("og", 1.050)
        
        # 1. Gather Context
        yeast_specs = search_yeast_meta(yeast_name) if yeast_name != "Unknown" else {}
        
        # Calculate Real-time Velocity (Last 24h)
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=24)
        data = query_batch_data(start_time, now)
        velocity = calculate_sg_velocity(data["sg_readings"], data["sg_times"]) if data["sg_readings"] else 0.0
        
        system_prompt = (
            "You are the 'Brewmaster', an expert in fermentation management. "
            "Provide proactive advice for the current batch. Suggest timing for diacetyl rests, dry hopping, or cold crashing. "
            "Be technical, extremely concise (max 3 sentences), and prioritize yeast-specific behavior."
        )
        
        context_parts = [
            f"Batch: {batch_name}",
            f"Yeast: {yeast_name}",
            f"Current SG: {sg} (OG: {og})",
            f"Current Temp: {temp}C",
            f"Fermentation Velocity: {velocity} gravity points/day"
        ]
        
        if yeast_specs and "error" not in yeast_specs:
            # Only include key specs to save context tokens/RAM
            context_parts.append(f"Yeast Specs: {yeast_specs.get('attenuation')}, {yeast_specs.get('temp_range')}")

        prompt = "\n".join(context_parts) + "\n\nProvide specific proactive recommendations for the next 24-48 hours."

        # 2. Call Ollama with Waste Management (keep_alive: 0)
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "keep_alive": 0 # Immediately unload model from RAM after generation
            }
            logger.info(f"Sending resource-optimized request to Ollama: {context_parts[-1]}")
            res = requests.post(ollama_url, json=payload, timeout=15)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "advice": text.strip(), "source": "ollama"}
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
                "keep_alive": 0
            }
            res = requests.post(ollama_url, json=payload, timeout=15)
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
        
        status = get_status_dict()
        sg = status.get("sg", 1.050)
        target_fg = float(get_config("target_fg") or 1.010)
        
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
                "keep_alive": 0
            }
            
            res = requests.post(ollama_url, json=payload, timeout=60)
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
                "keep_alive": 0
            }
            res = requests.post(ollama_url, json=payload, timeout=15)
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
            res = requests.post(ollama_url, json=payload, timeout=60)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "response": text.strip(), "source": "ollama"}
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
            res = requests.post(ollama_url, json=payload, timeout=60)
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
    produce a quality assessment. Uses keep_alive: 0 to unload the model
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
                "keep_alive": 0,
            }
            logger.info(f"Generating brew day evaluation for {batch_name}")
            res = requests.post(ollama_url, json=payload, timeout=60)
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
