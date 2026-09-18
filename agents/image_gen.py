import os
import io
from dotenv import load_dotenv
from google import genai
from huggingface_hub import InferenceClient

load_dotenv()
_gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

NANO_BANANA_MODEL = "gemini-2.5-flash-image"
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"


def _build_prompt(topic):
    return (
        f"A clean, professional editorial illustration representing the "
        f"concept of: {topic}. Minimalist, modern, high quality, suitable "
        f"as an article header image."
    )


def _try_nano_banana(topic):
    response = _gemini_client.models.generate_content(
        model=NANO_BANANA_MODEL,
        contents=_build_prompt(topic),
    )
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
    raise ValueError("Nano Banana returned no image data")


def _try_hugging_face(topic):
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN not set")

    client = InferenceClient(api_key=token)
    image = client.text_to_image(prompt=_build_prompt(topic), model=HF_MODEL)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def generate_header_image(topic):
    try:
        return _try_nano_banana(topic)
    except Exception as e:
        print(f"⚠️ Nano Banana failed: {e}. Falling back to Hugging Face.")

    try:
        return _try_hugging_face(topic)
    except Exception as e:
        print(f"⚠️ Hugging Face fallback also failed: {e}")
        return None