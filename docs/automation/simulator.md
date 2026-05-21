# AI Brew Simulator

The Simulator is a powerful AI-driven tool that predicts your fermentation journey before you brew.

## Features

### 1. Brew Day Prediction
- Takes your grain bill (weight and potential), target volume, and system efficiency.
- Predicts Original Gravity (OG) using standardized yield points mathematics.

### 2. Fermentation Timeline
- Takes the predicted OG and your selected Yeast strain.
- Cross-references historical brewing data and manufacturer specifications to determine likely attenuation and predict Final Gravity (FG).
- Plots a mathematical 14-day fermentation curve mapping the specific gravity drop across four phases: Lag, Active, Diacetyl Rest, and Terminal.

### 3. Ollama AI Insight
- Runs a Monte Carlo simulation over the yeast variance to calculate the 5th and 95th percentile risk of stalling.
- Sends these statistics to a local LLaMA 3 instance (via Ollama) to generate concise, expert-level proactive advice on how to mitigate stall risk.

## API Reference

### `POST /api/automation/simulate/timeline`
Generates the fermentation timeline and retrieves AI advice.

**Payload:**
```json
{
  "efficiency": 75,
  "volume": 23,
  "yeast": "US-05",
  "grains": [
    { "weight_kg": 5.0, "potential": 1.037 }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "llm_analysis": "Based on 30 historical batches with US-05, there is a 5% risk of stalling at 1.018. Consider pitching a healthy starter and ensuring oxygenation to mitigate this risk.",
    "timeline": [
      { "day": 1, "expected_sg": 1.050, "phase": "Lag Phase" },
      { "day": 2, "expected_sg": 1.042, "phase": "Active Fermentation" }
    ]
  }
}
```
