import os
import requests
import numpy as np
from typing import Optional
from datetime import datetime, timezone
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
            prompt = "Context of previous messages:\n" + "\n".join([f"{m['role']}: {m['content']}" for m in history]) + "\n\nUser: " + message

        payload = {
            "model": get_config("ollama_model") or "llama3:latest",
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }

        try:
            logger.info(f"Sending request to Ollama ({ollama_url}) with model {payload.get('model')}")
            res = requests.post(ollama_url, json=payload, timeout=60)
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
        
        status = get_status_dict()
        batch_name = status.get("batch_name", "the current batch")
        yeast_name = get_config("yeast_name") or "Unknown"
        sg = status.get("sg", "N/A")
        temp = status.get("temp", "N/A")
        og = status.get("og", 1.050)
        
        # 1. Gather Context
        yeast_specs = search_yeast_meta(yeast_name) if yeast_name != "Unknown" else {}
        yeast_history = analyze_yeast_history(yeast_name)
        
        system_prompt = (
            "You are the 'Brewmaster', an expert in fermentation management. "
            "Provide proactive advice for the current batch. Suggest timing for diacetyl rests, dry hopping, or cold crashing. "
            "Be technical, concise, and prioritize yeast-specific behavior."
        )
        
        context_parts = [
            f"Batch: {batch_name}",
            f"Yeast: {yeast_name}",
            f"Current SG: {sg} (OG: {og})",
            f"Current Temp: {temp}C"
        ]
        
        if yeast_specs and "error" not in yeast_specs:
            context_parts.append(f"Yeast Specs: {yeast_specs}")
            
        if yeast_history:
            context_parts.append(f"Historical Performance in this brewery: {yeast_history}")

        prompt = "\n".join(context_parts) + "\n\nProvide 2-3 specific proactive recommendations for the next 24-48 hours."

        # 2. Call Ollama
        ollama_host = os.environ.get("OLLAMA_HOST", get_config("ollama_host") or "ollama")
        ollama_url = f"http://{ollama_host}:11434/api/generate"
        
        try:
            payload = {
                "model": get_config("ollama_model") or "llama3:latest",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False
            }
            res = requests.post(ollama_url, json=payload, timeout=30)
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
                "stream": False
            }
            res = requests.post(ollama_url, json=payload, timeout=20)
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
                "stream": False
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
