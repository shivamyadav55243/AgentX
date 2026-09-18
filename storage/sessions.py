import json
import os
import uuid
from datetime import datetime

STORAGE_FILE = "storage/sessions.json"


def _load_all():
    if not os.path.exists(STORAGE_FILE):
        return {}
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(sessions):
    os.makedirs("storage", exist_ok=True)
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


def create_session():
    sessions = _load_all()
    session_id = uuid.uuid4().hex[:12]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sessions[session_id] = {
        "id": session_id,
        "title": "New chat",
        "created": now,
        "updated": now,
        "messages": [],
    }
    _save_all(sessions)
    return sessions[session_id]


def list_sessions():
    sessions = _load_all()
    items = list(sessions.values())
    items.sort(key=lambda s: s["updated"], reverse=True)
    return [{"id": s["id"], "title": s["title"], "updated": s["updated"]} for s in items]


def get_session(session_id):
    return _load_all().get(session_id)


def save_message(session_id, message):
    sessions = _load_all()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id, "title": "New chat",
            "created": now, "updated": now, "messages": [],
        }

    session = sessions[session_id]
    session["messages"].append(message)
    session["updated"] = now

    if session["title"] == "New chat" and message.get("role") == "user":
        words = message["content"].split()[:6]
        suffix = "…" if len(message["content"].split()) > 6 else ""
        session["title"] = " ".join(words) + suffix

    _save_all(sessions)
    return session


def get_last_session_id():
    sessions = _load_all()
    if not sessions:
        return None
    items = list(sessions.values())
    items.sort(key=lambda s: s["updated"], reverse=True)
    return items[0]["id"]