import os
from dotenv import load_dotenv
from google import genai

# Load the API key from .env
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def run_agent(topic):
    print(f"\n🔍 Researching: {topic}\n")

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=f"Give me a well-organized research summary on: {topic}. Include key facts, context, and 3-5 important points."
    )

    summary = response.text
    print(summary)
    return summary

if __name__ == "__main__":
    topic = input("Enter a topic to research: ")
    run_agent(topic)