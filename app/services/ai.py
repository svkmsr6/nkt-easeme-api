import json, logging
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from app.core.config import settings

log = logging.getLogger(__name__)

SYSTEM = (
  "You are an emotion-first micro-intervention selector for task initiation.\n"
  "Given: physical sensation, internal narrative, and an emotion label, you will:\n"
  "1) Identify primary barrier pattern: perfectionism | overwhelm | decision_fatigue | anxiety_dread.\n"
  "2) Select one technique: permission_protocol | single_next_action | choice_elimination | one_minute_entry.\n"
  "3) Return JSON: {\"pattern\":\"...\",\"technique_id\":\"...\",\"message\":\"...\",\"duration_seconds\":...}\n"
  "Techniques:\n"
  "- permission_protocol: for perfectionism/fear of failure; duration 300s with gentle framing.\n"
  "- single_next_action: for overwhelm; duration 0 (user-initiated) or 60 if timer is useful.\n"
  "- choice_elimination: for decision fatigue; duration 300s but include a 10s lead-in.\n"
  "- one_minute_entry: for anxiety/task dread; duration 60s.\n"
)

FALLBACKS = {
  "perfectionism": {
    "technique_id": "permission_protocol",
    "message": "Your only goal for 5 minutes: create it imperfectly. Make it worse than you think it should be.",
    "duration_seconds": 300,
  },
  "overwhelm": {
    "technique_id": "single_next_action",
    "message": "What’s the smallest physical action? e.g., just open the doc and type a title.",
    "duration_seconds": 60,
  },
  "decision_fatigue": {
    "technique_id": "choice_elimination",
    "message": "Don’t choose. Do this next: open the file and write 3 bullets. Starting in 10 seconds…",
    "duration_seconds": 300,
  },
  "anxiety_dread": {
    "technique_id": "one_minute_entry",
    "message": "Commit to 60 seconds only. Full permission to stop after. Timer set.",
    "duration_seconds": 60,
  },
}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def choose_intervention(payload: dict) -> dict:
    """
    Returns: dict(pattern, technique_id, message, duration_seconds)
    """
    user_context = {
      "task_description": payload["task_description"],
      "physical_sensation": payload["physical_sensation"],
      "internal_narrative": payload["internal_narrative"],
      "emotion_label": payload["emotion_label"],
    }
    req = {
      "model": settings.OPENAI_MODEL,
      "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Context:\n{json.dumps(user_context)}\nReturn ONLY JSON."}
      ],
      "temperature": settings.OPENAI_TEMPERATURE,
      "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    try:
        # Use same timeout configuration as emotion_labels - 5 minutes
        timeout_config = httpx.Timeout(connect=30.0, read=280.0, write=15.0, pool=300.0)
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", json=req, headers=headers)
            r.raise_for_status()
            data = r.json()
            raw = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw)
            pattern = parsed.get("pattern") or "anxiety_dread"
            tech = parsed.get("technique_id") or FALLBACKS[pattern]["technique_id"]
            msg = parsed.get("message") or FALLBACKS[pattern]["message"]
            dur = int(parsed.get("duration_seconds") or FALLBACKS[pattern]["duration_seconds"])
            return {"pattern": pattern, "technique_id": tech, "message": msg, "duration_seconds": dur}
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError, ValueError) as e:
        log.error("OpenAI API error, using fallback: %s", e)
        # Use anxiety_dread as default fallback
        fallback = FALLBACKS["anxiety_dread"]
        return {
            "pattern": "anxiety_dread",
            "technique_id": fallback["technique_id"], 
            "message": fallback["message"],
            "duration_seconds": fallback["duration_seconds"]
        }

@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
async def emotion_labels(payload: dict) -> list[str]:
    """Lightweight label suggestions (2-3 options)."""
    prompt = (
      "Suggest 2-3 concise emotion labels based on:\n"
      f"- physical_sensation: {payload['physical_sensation']}\n"
      f"- internal_narrative: {payload['internal_narrative']}\n"
      f"- task: {payload['task_description']}\n"
      "Return ONLY a JSON object with this format: {\"labels\": [\"emotion1\", \"emotion2\", \"emotion3\"]}"
    )
    req = {
      "model": settings.OPENAI_MODEL,
      "messages": [{"role":"user","content":prompt}],
      "temperature": 0.2,
      "response_format": {"type":"json_object"}
    }
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    log.info(f"Making OpenAI emotion labels request with API key prefix: {settings.OPENAI_API_KEY[:12]}...")
    log.info(f"Request timeout: 300.0s (5 minutes), model: {settings.OPENAI_MODEL}")
    
    # Configure timeout with more granular control - increased to 5 minutes
    timeout_config = httpx.Timeout(
        connect=30.0,   # Connection timeout - 30 seconds for slow networks
        read=280.0,     # Read timeout - 280 seconds for API processing
        write=15.0,     # Write timeout - 15 seconds for request upload
        pool=300.0      # Total timeout - 300 seconds (5 minutes)
    )
    
    # Configure client with retry-friendly settings
    client_config = {
        "timeout": timeout_config,
        "follow_redirects": True,
        "verify": True  # Ensure SSL verification
    }
    
    async with httpx.AsyncClient(**client_config) as client:
        try:
            r = await client.post("https://api.openai.com/v1/chat/completions", json=req, headers=headers)
            r.raise_for_status()
            data = r.json()
            parsed = json.loads(data["choices"][0]["message"]["content"])
            opts = parsed.get("emotion_options") or parsed.get("labels") or []
            return [o for o in opts][:3] or ["Fear of judgment","Perfectionism anxiety","Performance pressure"]
        except httpx.TimeoutException as e:
            log.warning(f"OpenAI API timeout after {timeout_config.pool}s: {e}")
            log.error("Consider checking network connectivity or OpenAI API status")
            return ["Fear of judgment","Perfectionism anxiety","Performance pressure"]
        except httpx.ConnectError as e:
            log.warning(f"OpenAI API connection error: {e}")
            log.error("Unable to connect to OpenAI API - check network/firewall")
            return ["Fear of judgment","Perfectionism anxiety","Performance pressure"]
        except httpx.HTTPStatusError as e:
            log.warning(f"OpenAI API HTTP error: {e.response.status_code}")
            log.error(f"Response body: {e.response.text}")
            return ["Fear of judgment","Perfectionism anxiety","Performance pressure"]
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"OpenAI API response parsing error: {e}")
            return ["Fear of judgment","Perfectionism anxiety","Performance pressure"]
        except Exception as e:
            log.warning(f"Unexpected error calling OpenAI API: {type(e).__name__}: {e}")
            return ["Fear of judgment","Perfectionism anxiety","Performance pressure"]
