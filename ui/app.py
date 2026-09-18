import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64
import streamlit as st
import streamlit.components.v1 as components
from orchestrator import run_pipeline
from storage.memory import load_all_reports
from storage.pdf_export import markdown_to_pdf
from agents.chatbot import chat_reply
from agents.router import classify_intent

st.set_page_config(
    page_title="AgentX",
    page_icon=":material/psychology:",
    layout="wide",
)

css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "history_open" not in st.session_state:
    st.session_state.history_open = False

SUGGESTIONS = [
    "The rise of AI agents",
    "History of the internet",
    "Climate change solutions",
    "The future of remote work",
]


def queue_suggestion():
    picked = st.session_state.get("topic_pills")
    if picked:
        st.session_state.pending_message = picked


# ---------- floating toggle button ----------
st.markdown('<div class="history-toggle-wrap">', unsafe_allow_html=True)
if st.button("☰", key="history_toggle_btn", help="Toggle history panel"):
    st.session_state.history_open = not st.session_state.history_open
st.markdown('</div>', unsafe_allow_html=True)

st.title("AgentX")
st.caption("Autonomous multi-agent research and intelligence — talk to it, or ask it to research anything")
st.markdown(
    ":orange-badge[Planner] :orange-badge[Researcher] "
    ":orange-badge[Writer] :orange-badge[Critic] :orange-badge[Rodrik]"
)

if st.session_state.history_open:
    history_col, main_col = st.columns([1, 3.3], gap="medium")
else:
    main_col = st.container()
    history_col = None

# ================= HISTORY PANEL (left) =================
if history_col is not None:
    with history_col:
        st.markdown('<div class="history-panel">', unsafe_allow_html=True)
        st.markdown("##### History")
        reports = load_all_reports()

        if not reports:
            st.caption("No reports yet.")
        else:
            for r in reports:
                short_label = " ".join(r["topic"].split()[:4])
                if st.button(short_label, key=f"hist_{r['timestamp']}_{r['topic']}", use_container_width=True):
                    image = base64.b64decode(r["image_b64"]) if r.get("image_b64") else None
                    try:
                        pdf_bytes = markdown_to_pdf(r["topic"], r["report"])
                    except Exception:
                        pdf_bytes = None
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Here's the report on **{r['topic']}** from {r['timestamp']}:\n\n{r['report']}",
                        "image": image,
                        "pdf": pdf_bytes,
                        "topic": r["topic"],
                    })
                    st.rerun()
                st.caption(r["timestamp"])
        st.markdown('</div>', unsafe_allow_html=True)

# ================= MAIN CHAT AREA =================
with main_col:
    st.pills(
        "Try a topic",
        SUGGESTIONS,
        selection_mode="single",
        key="topic_pills",
        on_change=queue_suggestion,
    )

    chat_box = st.container(height=560, border=True)
    with chat_box:
        for idx, turn in enumerate(st.session_state.chat_history):
            with st.chat_message(turn["role"]):
                st.markdown(turn["content"])
                if turn.get("image"):
                    st.image(turn["image"], use_container_width=True)
                if turn.get("pdf"):
                    safe_name = (turn.get("topic") or "report").replace(" ", "_")
                    st.download_button(
                        "Download PDF",
                        data=turn["pdf"],
                        file_name=f"{safe_name}_report.pdf",
                        mime="application/pdf",
                        icon=":material/download:",
                        key=f"pdf_dl_{idx}",
                    )
        st.markdown('<div id="chat-end"></div>', unsafe_allow_html=True)
        components.html(
            """
            <script>
                var el = window.parent.document.getElementById('chat-end');
                if (el) { el.scrollIntoView({behavior: 'instant', block: 'end'}); }
            </script>
            """,
            height=0,
        )

    user_msg = st.chat_input("Ask me anything, or say 'research ...' for a full report")
    incoming = user_msg or st.session_state.pop("pending_message", None)

    if incoming:
        st.session_state.chat_history.append({"role": "user", "content": incoming})

        intent_info = classify_intent(incoming)

        if intent_info["intent"] == "research":
            topic = intent_info["topic"]
            status = st.status(f"Researching: {topic}", expanded=True)

            def on_progress(message):
                status.write(message)

            try:
                report, header_image = run_pipeline(topic, on_progress=on_progress)
                status.update(label="Research complete", state="complete", expanded=False)
                try:
                    pdf_bytes = markdown_to_pdf(topic, report)
                except Exception:
                    pdf_bytes = None
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": report,
                    "image": header_image,
                    "pdf": pdf_bytes,
                    "topic": topic,
                })
            except Exception as exc:
                status.update(label="Research failed", state="error")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Sorry, the research pipeline hit an error: {exc}",
                })
        else:
            with st.spinner("Rodrik is thinking..."):
                reply = chat_reply(st.session_state.chat_history[:-1], incoming)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

        st.rerun()