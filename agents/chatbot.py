from agents.llm import generate_text

def chat_reply(history, user_message, max_retries=5):
    # Build a conversation transcript so the model has context
    transcript = ""
    for turn in history:
        role = "User" if turn["role"] == "user" else "Assistant"
        transcript += f"{role}: {turn['content']}\n"
    transcript += f"User: {user_message}\nAssistant:"

    prompt = f"""You are Rodrik, the built-in conversational assistant for AgentX —
an autonomous multi-agent research platform. You are separate from the research
pipeline (Planner/Researcher/Writer/Critic); you exist to chat naturally and
answer questions directly.

If asked your name, who you are, or what you are, respond as Rodrik — do not
mention being Gemini, Google, or any underlying model/provider.

Answer clearly and directly. Keep responses concise unless the user asks for
more detail. Here is the conversation so far:

{transcript}"""
    try:
        return generate_text(prompt, max_retries=max_retries)
    except Exception as e:
        print(f"⚠️ Chatbot failed: {e}")
        return "Sorry, I couldn't process that right now — please try again in a moment."