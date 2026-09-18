import os
import re
import threading
import time
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

GEMINI_MODEL = "gemini-3.6-flash"
# GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_MODEL = "openai/gpt-oss-20b"


_gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_lock = threading.Lock()
_last_gemini_call = 0.0

# Gemini free tier: 5 requests/minute. Groq's free tier is much higher,
# so no artificial pacing is applied to it.
MIN_GEMINI_INTERVAL_SECONDS = 13


def _retry_delay_seconds(error, fallback=20):
    text = str(error)
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", text, re.IGNORECASE)
    if match:
        return min(60.0, float(match.group(1)) + 1.0)
    match = re.search(r"'retryDelay': '([0-9]+)s'", text)
    if match:
        return min(60.0, float(match.group(1)) + 1.0)
    return fallback


def _is_rate_limit(error):
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "rate_limit" in text.lower()


def _call_groq(prompt):
    response = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise ValueError("Empty response from Groq")
    return text


def _call_gemini(prompt):
    global _last_gemini_call
    with _lock:
        wait = MIN_GEMINI_INTERVAL_SECONDS - (time.time() - _last_gemini_call)
        if wait > 0:
            print(f"⏳ Gemini pacing: waiting {wait:.0f}s…")
            time.sleep(wait)
        response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        _last_gemini_call = time.time()
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")
        return text


def generate_text(prompt, max_retries=5):
    """Try Groq first (fast, high free-tier limits). Fall back to Gemini on failure."""
    last_error = None

    # --- Try Groq first ---
    for attempt in range(1, max_retries + 1):
        try:
            return _call_groq(prompt)
        except Exception as e:
            last_error = e
            if _is_rate_limit(e) and attempt < max_retries:
                print(f"⚠️ Groq rate limit (attempt {attempt}). Retrying shortly…")
                time.sleep(2)
                continue
            print(f"⚠️ Groq failed: {e}. Falling back to Gemini.")
            break

    # --- Fallback to Gemini ---
    for attempt in range(1, max_retries + 1):
        try:
            return _call_gemini(prompt)
        except Exception as e:
            last_error = e
            if _is_rate_limit(e) and attempt < max_retries:
                delay = _retry_delay_seconds(e)
                print(f"⚠️ Gemini quota hit (attempt {attempt}). Waiting {delay:.0f}s…")
                time.sleep(delay)
                continue
            if attempt < max_retries:
                print(f"⚠️ Gemini attempt {attempt} failed: {e}")
                time.sleep(2)
                continue
            raise

    raise last_error