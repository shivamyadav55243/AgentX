import json
import os
import base64
from datetime import datetime

STORAGE_FILE = "storage/reports.json"

def save_report(topic, report, image=None):
    reports = load_all_reports()

    entry = {
        "topic": topic,
        "report": report,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "image_b64": base64.b64encode(image).decode("utf-8") if image else None
    }
    reports.insert(0, entry)

    os.makedirs("storage", exist_ok=True)
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)

    return entry

def load_all_reports():
    if not os.path.exists(STORAGE_FILE):
        return []
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)