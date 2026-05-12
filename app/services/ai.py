import os
import requests
import numpy as np
from typing import Optional
from datetime import datetime, timezone
from core.influx import query_api, INFLUX_BUCKET
from core.cache import cache
from core.config import get_config, logger

def generate_narrative(batch_data: dict) -> dict:
    """
    Generates a creative narrative log for a fermentation batch using AI.
    Tries local Ollama first, then falls back to configured API.
    """
    try:
        # 1. Prepare Prompt
        style = batch_data.get("style", "Beer")
        name = batch_data.get("name", "Unknown Batch")
        og = batch_data.get("og", 1.050)
        fg = batch_data.get("fg", 1.010)
        temp_avg = batch_data.get("temp_avg", 20.0)
        status = batch_data.get("status", "fermenting")
        
        prompt = (
            f"Write a short, engaging 2-3 sentence 'Brewmaster Log' for a {style} named '{name}'. "
            f"Initial Gravity: {og:.3f}, Current Gravity: {fg:.3f}, Average Temp: {temp_avg:.1f}C. "
            f"The fermentation is {status}. Be creative but professional."
        )

        # 2. Try Local Ollama (Edge AI)
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "localhost")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        try:
            payload = {
                "model": get_config("ollama_model") or "llama3",
                "prompt": prompt,
                "stream": False
            }
            res = requests.post(ollama_url, json=payload, timeout=15)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "narrative": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.debug(f"Ollama not available at {ollama_url}, falling back. Error: {e}")

        # 3. Fallback to Cloud (Gemini via Proxy or direct if key available)
        # For now, we'll return a template-based narrative if AI fails
        logger.warning("AI Narrative generation failed or not configured, using template")
        
        templates = [
            f"The {style} '{name}' is making steady progress at {temp_avg:.1f}C. Gravity has dropped to {fg:.3f}, showing healthy yeast activity.",
            f"Monitoring the {style} fermenting in the lab. Current SG is {fg:.3f}. The yeast seems happy with the stable {temp_avg:.1f}C environment.",
            f"Log entry for {name}: Fermentation is {status}. Moving from {og:.3f} towards the target. Everything is looking nominal."
        ]
        import random
        return {"status": "fallback", "narrative": random.choice(templates), "source": "template"}

    except Exception as e:
        logger.error(f"Narrative Error: {e}")
        return {"error": str(e)}

def generate_chat_response(message: str, history: Optional[list] = None) -> dict:
    """
    Experimental 'Brewmaster' chat response using local Ollama.
    """
    try:
        from services.status import get_status_dict
        status = get_status_dict()
        
        # 1. Prepare Context
        batch_name = status.get("batch_name", "Unknown")
        sg = status.get("sg", "N/A")
        temp = status.get("temp", "N/A")
        
        system_prompt = (
            "You are the 'Brewmaster', a professional and helpful brewing assistant. "
            "You have access to the current fermentation data. Be concise, technical, and encouraging."
        )
        
        prompt = (
            f"Current batch: {batch_name}\n"
            f"Current Specific Gravity: {sg}\n"
            f"Current Temperature: {temp}C\n"
            f"User: {message}\n"
            "Brewmaster:"
        )

        # 2. Call Ollama
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "localhost")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        payload = {
            "model": get_config("ollama_model") or "llama3",
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }
        
        try:
            res = requests.post(ollama_url, json=payload, timeout=30)
            if res.status_code == 200:
                text = res.json().get("response")
                if text:
                    return {"status": "success", "response": text.strip(), "source": "ollama"}
        except Exception as e:
            logger.debug(f"Ollama chat failed: {e}")

        return {
            "status": "fallback", 
            "response": "The Brewmaster is currently offline. I can see your batch is at " + str(sg) + " SG, but I can't provide detailed advice right now.",
            "source": "template"
        }

    except Exception as e:
        logger.error(f"Chat AI Error: {e}")
        return {"status": "error", "message": str(e)}

def analyze_yeast_history(yeast_name):
    """
    Analyzes measurements for a specific yeast strain over the last 90 days
    to determine 'Normal Behavior'.
    
    Returns:
       dict: { "avg_rate": float (points/day), "attenuation": float (%), "samples": int }
       OR None if insufficient data.
    """
    if not yeast_name or yeast_name == "Unknown":
        return None

    # 0. Check Cache
    cache_key = f"yeast_history_{yeast_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    # 1. Query Data (Last 90 days)
    # We want ALL calibrated readings for this yeast
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -90d)
      |> filter(fn: (r) => r["_measurement"] == "calibrated_readings")
      |> filter(fn: (r) => r["yeast"] == "{yeast_name}")
      |> filter(fn: (r) => r["_field"] == "sg")
      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
      |> yield(name: "mean")
    '''
    
    try:
        tables = query_api.query(query)
        readings = []
        
        for table in tables:
            for record in table.records:
                readings.append((record.get_time(), record.get_value()))
        
        if not readings:
            return None

        # 2. Separate into Batches
        # Logic: If gap > 72 hours (3 days), it's a new batch
        batches = []
        current_batch = []
        last_time = None
        
        # Sort by time just in case
        readings.sort(key=lambda x: x[0])
        
        for r_time, r_val in readings:
            if last_time is None:
                current_batch.append((r_time, r_val))
            else:
                diff = (r_time - last_time).total_seconds()
                if diff > (72 * 3600): # 72 hours
                    if len(current_batch) > 20: # Only count significant batches
                        batches.append(current_batch)
                    current_batch = [(r_time, r_val)]
                else:
                    current_batch.append((r_time, r_val))
            last_time = r_time
            
        if len(current_batch) > 20:
            batches.append(current_batch)
            
        # 3. Analyze Each Batch
        # We exclude the "Current" batch if it looks active (last reading < 24h ago)
        # Actually, user said: "Exclude the current batch".
        # We can just filter out any batch where the last point is very recent (e.g. < 24h)
        
        historic_batches = []
        now = datetime.now(timezone.utc)
        
        for b in batches:
            last_point_time = b[-1][0]
            if (now - last_point_time).total_seconds() > (24 * 3600):
                historic_batches.append(b)
                
        if len(historic_batches) < 1:
            return None # Not enough history

        rates = []
        attenuations = []
        
        for b in historic_batches:
            # Calculate Rate: (Start SG - End SG) / Days
            start_sg = b[0][1]
            end_sg = b[-1][1]
            duration_days = (b[-1][0] - b[0][0]).total_seconds() / 86400
            
            if duration_days > 1.0:
                drop = start_sg - end_sg
                rate = drop / duration_days # points per day
                
                # Attenuation (Apparent): (OG - FG) / (OG - 1)
                # We assume Start SG is close to OG for this math
                if start_sg > 1.0:
                    att = (start_sg - end_sg) / (start_sg - 1)
                    attenuations.append(att)
                
                rates.append(rate)

        if not rates:
            return None
            
        result = {
            "avg_rate": float(np.mean(rates)),
            "avg_attenuation": float(np.mean(attenuations)) if attenuations else 0.75,
            "samples": len(historic_batches)
        }

        # Cache result for 1 hour
        cache.set(cache_key, result, ttl=3600)

        return result

    except Exception as e:
        print(f"AI Error: {e}")
        return None
