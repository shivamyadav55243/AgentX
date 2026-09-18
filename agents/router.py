import json
from agents.llm import generate_text


def classify_intent(message, max_retries=3):
    prompt = f"""Classify the user's message into exactly one of three intents:

"research" — wants a thorough, multi-source researched report on a topic.
Trigger phrases: "research X", "write a report on X", "find out about X".

"image" — wants an image, picture, illustration, or artwork generated.
Trigger phrases: "generate an image of X", "draw X", "create a picture of X",
"make an illustration of X".

"chat" — casual conversation, opinions, greetings, or quick questions that
don't need a report or an image.

Respond ONLY with compact JSON, nothing else:
{{"intent": "research" or "image" or "chat", "topic": "<short subject phrase if research or image, else empty string>"}}

Message: "{message}\""""

    try:
        text = generate_text(prompt, max_retries=max_retries)
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        intent = data.get("intent", "chat")
        topic = data.get("topic", "") or message
        if intent not in ("research", "image", "chat"):
            intent = "chat"
        return {"intent": intent, "topic": topic}
    except Exception as e:
        print(f"⚠️ Intent classification failed: {e}. Defaulting to chat.")
        return {"intent": "chat", "topic": message}