import json
import re
from agents.llm import generate_text

_PLACEHOLDER_PATTERN = re.compile(r"^question\s*\d+$", re.IGNORECASE)


def plan(topic, max_retries=3):
    prompt = f"""Analyze the topic "{topic}" and write 2 to 6 specific, real
research sub-questions about it (more for broad topics, fewer for narrow ones).

Do NOT copy the example format below literally — write actual, topic-specific
questions about "{topic}".

Respond ONLY with a JSON array of strings, nothing else. Example shape only
(write your own real questions, not these words):
["What caused X to happen?", "How did Y change over time?"]"""

    for attempt in range(1, max_retries + 1):
        try:
            text = generate_text(prompt, max_retries=1)
            text = text.replace("```json", "").replace("```", "").strip()
            sub_questions = json.loads(text)

            if not isinstance(sub_questions, list) or len(sub_questions) == 0:
                raise ValueError("Planner returned an empty or invalid list")

            if any(_PLACEHOLDER_PATTERN.match(q.strip()) for q in sub_questions):
                raise ValueError("Planner echoed placeholder text instead of real questions")

            return sub_questions
        except Exception as e:
            print(f"⚠️ Planner attempt {attempt} failed: {e}")
            if attempt == max_retries:
                return [f"General overview of {topic}"]