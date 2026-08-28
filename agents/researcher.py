import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def research(sub_question, max_retries=3):
    prompt = f"""Research this question and give a concise, factual answer
with key details: {sub_question}"""

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
            print(f"⚠️ Researcher attempt {attempt} failed for '{sub_question}': {e}")
            if attempt == max_retries:
                return f"[Research failed for this question after {max_retries} attempts]"
            time.sleep(2)