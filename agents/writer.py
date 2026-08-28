import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def write_report(topic, findings, max_retries=3):
    findings_text = "\n\n".join(
        [f"Q: {q}\nA: {a}" for q, a in findings]
    )

    prompt = f"""You are writing a final research report on: {topic}

Here is the raw research gathered:

{findings_text}

Combine this into one clear, well-organized report with a short intro,
organized sections, and a brief conclusion. Avoid repeating the raw Q&A format."""

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )
            if not response.text or len(response.text.strip()) == 0:
                raise ValueError("Empty response from model")
            return response.text

        except Exception as e:
            print(f"⚠️ Writer attempt {attempt} failed: {e}")
            if attempt == max_retries:
                # Fallback: just stitch findings together manually
                fallback = f"# Report on {topic}\n\n(Note: AI writer unavailable — showing raw research)\n\n" + findings_text
                return fallback
            time.sleep(2)