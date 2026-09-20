import os
import sys
import base64
import markdown as md
from flask import Flask, request, jsonify, send_from_directory, Response
import queue
import threading
import json
from groq import Groq
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import run_pipeline
from agents.chatbot import chat_reply
from agents.router import classify_intent
from agents.image_gen import generate_header_image
from storage.memory import load_all_reports
from storage.pdf_export import markdown_to_pdf
from storage.sessions import (
    create_session,
    list_sessions,
    get_session,
    save_message,
    get_last_session_id,
    delete_session,
)

app = Flask(__name__, static_folder="web", static_url_path="")


def _b64(data):
    return base64.b64encode(data).decode("utf-8") if data else None


def _md_to_html(text):
    return md.markdown(text or "", extensions=["tables", "fenced_code"])

_groq_whisper_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------- report history (existing) ----------
@app.route("/api/history", methods=["GET"])
def get_history():
    reports = load_all_reports()
    out = [
        {"id": i, "topic": r["topic"], "timestamp": r["timestamp"],
         "label": " ".join(r["topic"].split()[:4])}
        for i, r in enumerate(reports)
    ]
    return jsonify(out)

@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "no audio file"}), 400

    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()

    try:
        print(f"🎙️ Received audio: {len(audio_bytes)} bytes")
        transcription = _groq_whisper_client.audio.transcriptions.create(
            file=("audio.webm", io.BytesIO(audio_bytes)),
            model="whisper-large-v3",
        )
        print(f"🎙️ Transcription result: '{transcription.text}'")
        return jsonify({"text": transcription.text})
    except Exception as e:
        print(f"⚠️ Transcription failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/history/<int:report_id>", methods=["GET"])
def get_history_item(report_id):
    reports = load_all_reports()
    if report_id < 0 or report_id >= len(reports):
        return jsonify({"error": "not found"}), 404
    r = reports[report_id]
    try:
        pdf_bytes = markdown_to_pdf(r["topic"], r["report"])
    except Exception:
        pdf_bytes = None
    return jsonify({
        "topic": r["topic"],
        "timestamp": r["timestamp"],
        "content_html": _md_to_html(r["report"]),
        "image_b64": r.get("image_b64"),
        "pdf_b64": _b64(pdf_bytes),
    })


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session_route(session_id):
    deleted = delete_session(session_id)
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": True})
# ---------- chat sessions (new) ----------
@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    return jsonify(list_sessions())


@app.route("/api/sessions", methods=["POST"])
def new_session():
    return jsonify(create_session())


@app.route("/api/sessions/last", methods=["GET"])
def last_session():
    session_id = get_last_session_id()
    if not session_id:
        return jsonify(None)
    return jsonify(get_session(session_id))


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session_route(session_id):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "not found"}), 404
    return jsonify(session)


# ---------- streaming chat/research/image ----------
@app.route("/api/message/stream", methods=["POST"])
def stream_message():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    session_id = data.get("session_id")

    if not message:
        return jsonify({"error": "empty message"}), 400

    if session_id:
        save_message(session_id, {"role": "user", "content": message})

    q = queue.Queue()

    def worker():
        def _final(payload):
            if session_id:
                save_message(session_id, {**payload, "role": "assistant"})
            q.put(payload)

        try:
            intent_info = classify_intent(message)

            if intent_info["intent"] == "research":
                topic = intent_info["topic"] or message

                def on_progress(msg):
                    q.put({"type": "step", "label": msg})

                try:
                    report, header_image = run_pipeline(topic, on_progress=on_progress)
                except Exception as exc:
                    _final({"type": "final", "intent": "research",
                            "content_html": f"<p>Sorry, the research pipeline hit an error: {exc}</p>",
                            "topic": topic})
                    return
                try:
                    pdf_bytes = markdown_to_pdf(topic, report)
                except Exception:
                    pdf_bytes = None
                _final({"type": "final", "intent": "research",
                        "content_html": _md_to_html(report), "topic": topic,
                        "image_b64": _b64(header_image), "pdf_b64": _b64(pdf_bytes)})

            elif intent_info["intent"] == "image":
                topic = intent_info["topic"] or message
                q.put({"type": "step", "label": f"Generating an image of: {topic}"})
                try:
                    image_bytes = generate_header_image(topic)
                except Exception as exc:
                    image_bytes = None
                    print(f"⚠️ Image generation failed: {exc}")
                if image_bytes:
                    _final({"type": "final", "intent": "image",
                            "content_html": f"<p>Here's your image for: <strong>{topic}</strong></p>",
                            "image_b64": _b64(image_bytes), "topic": topic})
                else:
                    _final({"type": "final", "intent": "image",
                            "content_html": "<p>Sorry, image generation failed. Please try again.</p>"})

            else:
                q.put({"type": "step", "label": "Thinking..."})
                reply = chat_reply(history, message)
                _final({"type": "final", "intent": "chat", "content_html": _md_to_html(reply)})

        except Exception as exc:
            _final({"type": "final", "intent": "error",
                    "content_html": f"<p>Unexpected error: {exc}</p>"})
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ---------- non-streaming fallback (kept for compatibility) ----------
@app.route("/api/message", methods=["POST"])
def post_message():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "empty message"}), 400

    intent_info = classify_intent(message)

    if intent_info["intent"] == "research":
        topic = intent_info["topic"] or message
        try:
            report, header_image = run_pipeline(topic, on_progress=print)
        except Exception as exc:
            return jsonify({
                "role": "assistant", "intent": "research",
                "content_html": f"<p>Sorry, the research pipeline hit an error: {exc}</p>",
                "topic": topic,
            })
        try:
            pdf_bytes = markdown_to_pdf(topic, report)
        except Exception:
            pdf_bytes = None
        return jsonify({
            "role": "assistant", "intent": "research",
            "content_html": _md_to_html(report), "topic": topic,
            "image_b64": _b64(header_image), "pdf_b64": _b64(pdf_bytes),
        })

    elif intent_info["intent"] == "image":
        topic = intent_info["topic"] or message
        try:
            image_bytes = generate_header_image(topic)
        except Exception as exc:
            image_bytes = None
            print(f"⚠️ Image generation failed: {exc}")
        if image_bytes:
            return jsonify({
                "role": "assistant", "intent": "image",
                "content_html": f"<p>Here's your image for: <strong>{topic}</strong></p>",
                "image_b64": _b64(image_bytes), "topic": topic,
            })
        return jsonify({
            "role": "assistant", "intent": "image",
            "content_html": "<p>Sorry, image generation failed. Please try again.</p>",
        })

    else:
        reply = chat_reply(history, message)
        return jsonify({"role": "assistant", "intent": "chat", "content_html": _md_to_html(reply)})


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True, port=5000)