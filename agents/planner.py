import os
import json
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def plan(topic, max_retries=3):
    prompt = f"""Analyze the topic "{topic}" and decide how many sub-questions
it needs for thorough research (between 2 and 6, based on complexity — simple
topics need fewer, broad topics need more).

Respond ONLY with a JSON array of strings, nothing else.
Example: ["question 1", "question 2", "question 3"]"""

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )
            text = response.text.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            sub_questions = json.loads(text)

            if not isinstance(sub_questions, list) or len(sub_questions) == 0:
                raise ValueError("Planner returned an empty or invalid list")

            return sub_questions

        except Exception as e:
            print(f"⚠️ Planner attempt {attempt} failed: {e}")
            if attempt == max_retries:
                print("❌ Planner failed after all retries. Using a fallback question.")
                return [f"General overview of {topic}"]
            time.sleep(2)