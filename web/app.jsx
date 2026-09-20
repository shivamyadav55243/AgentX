const { useState, useEffect, useRef } = React;

const SUGGESTIONS = [
  "The rise of AI agents",
  "History of the internet",
  "Climate change solutions",
  "The future of remote work",
];

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [reactions, setReactions] = useState({});
  const endRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  async function refreshSessions() {
    const res = await fetch("/api/sessions");
    setSessions(await res.json());
  }

    async function deleteSession(e, id) {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;

    await fetch(`/api/sessions/${id}`, { method: "DELETE" });

    if (id === sessionId) {
      const remaining = sessions.filter((s) => s.id !== id);
      if (remaining.length > 0) {
        loadSession(remaining[0].id);
      } else {
        startNewChat();
      }
    }
    refreshSessions();
  }

  function shareSession(e, session) {
    e.stopPropagation();
    const text = `Check out my AgentX chat: "${session.title}"`;
    if (navigator.share) {
      navigator.share({ text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text);
    }
  }

  useEffect(() => {
    refreshSessions();
    (async () => {
      const res = await fetch("/api/sessions/last");
      const last = await res.json();
      if (last) {
        setSessionId(last.id);
        setMessages(rebuildMessages(last.messages));
      } else {
        const res2 = await fetch("/api/sessions", { method: "POST" });
        const created = await res2.json();
        setSessionId(created.id);
      }
    })();
  }, []);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  function rebuildMessages(stored) {
    return (stored || []).map((m) => ({
      role: m.role,
      content: m.content_html || m.content || "",
      isHtml: !!m.content_html,
      image: m.image_b64,
      pdf: m.pdf_b64,
      topic: m.topic,
    }));
  }

  async function startNewChat() {
    const res = await fetch("/api/sessions", { method: "POST" });
    const created = await res.json();
    setSessionId(created.id);
    setMessages([]);
    refreshSessions();
  }

  async function loadSession(id) {
    const res = await fetch(`/api/sessions/${id}`);
    const data = await res.json();
    setSessionId(id);
    setMessages(rebuildMessages(data.messages));
  }

  function handleAttachClick() {
    fileInputRef.current?.click();
  }

  function handleFileSelected(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setAttachedFile({ name: file.name, content: reader.result });
    reader.readAsText(file);
    e.target.value = "";
  }

  function removeAttachment() {
    setAttachedFile(null);
  }

  function copyMessage(index, text, isHtml) {
    let plain = text;
    if (isHtml) {
      const tmp = document.createElement("div");
      tmp.innerHTML = text;
      plain = tmp.innerText;
    }
    navigator.clipboard.writeText(plain).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    });
  }

  function toggleReaction(index, kind) {
    setReactions((prev) => {
      const current = prev[index];
      return { ...prev, [index]: current === kind ? null : kind };
    });
  }

  function shareMessage(text, isHtml) {
    let plain = text;
    if (isHtml) {
      const tmp = document.createElement("div");
      tmp.innerHTML = text;
      plain = tmp.innerText;
    }
    if (navigator.share) {
      navigator.share({ text: plain }).catch(() => {});
    } else {
      navigator.clipboard.writeText(plain);
    }
  }

  function regenerate(index) {
    for (let i = index - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        sendMessage(messages[i].content);
        return;
      }
    }
  }

  async function sendMessage(text) {
    let content = (text || input).trim();
    if (!content && !attachedFile) return;
    if (!sessionId) return;

    if (attachedFile) {
      content = `Attached file "${attachedFile.name}":\n\n${attachedFile.content}\n\n---\n\n${content || "Please look at this file."}`;
    }

    const displayContent = (text || input).trim() + (attachedFile ? ` 📎 ${attachedFile.name}` : "");

    setMessages((prev) => [...prev, { role: "user", content: displayContent }]);
    setInput("");
    setAttachedFile(null);
    setLoading(true);

    const stepsMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: "assistant", isSteps: true, steps: [] }]);

    try {
      const res = await fetch("/api/message/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          history: messages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const evt = JSON.parse(part.slice(6));

          if (evt.type === "step") {
            setMessages((prev) => {
              const copy = [...prev];
              const target = copy[stepsMsgIndex];
              if (target && target.isSteps) {
                copy[stepsMsgIndex] = { ...target, steps: [...target.steps, evt.label] };
              }
              return copy;
            });
          } else if (evt.type === "final") {
            setMessages((prev) => {
              const copy = [...prev];
              copy[stepsMsgIndex] = {
                role: "assistant",
                content: evt.content_html || "",
                isHtml: true,
                image: evt.image_b64,
                pdf: evt.pdf_b64,
                topic: evt.topic,
              };
              return copy;
            });
            refreshSessions();
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        copy[stepsMsgIndex] = { role: "assistant", content: "Something went wrong reaching the server." };
        return copy;
      });
    } finally {
      setLoading(false);
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());

        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");

        setInput("Transcribing...");
        try {
          const res = await fetch("/api/transcribe", { method: "POST", body: formData });
          const data = await res.json();
          setInput(data.text || "");
        } catch (err) {
          setInput("");
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch (err) {
      alert("Microphone access denied or unavailable.");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    setRecording(false);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  return (
    <div className="app-shell">
      <div className="top-bar">
        <button className={"history-toggle" + (historyOpen ? " open" : "")} onClick={() => setHistoryOpen(!historyOpen)} title="Toggle history">
          <span className="toggle-icon">☰</span>
        </button>
        <span className="top-bar-title">AgentX</span>
      </div>

      <div className={"history-panel" + (historyOpen ? "" : " closed")}>
        <button className="new-chat-btn" onClick={startNewChat}>+ New chat</button>
        <h4>Chats</h4>
        <div className="history-list">
          {sessions.length === 0 && <p className="muted">No chats yet.</p>}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={"history-item" + (s.id === sessionId ? " active" : "")}
              onClick={() => loadSession(s.id)}
            >
              <div className="history-item-main">
                <span className="history-label">{s.title}</span>
                <span className="history-time">{s.updated}</span>
              </div>

              <div className="history-item-actions">
                <button
                  className="icon-only-btn"
                  onClick={(e) => shareSession(e, s)}
                  title="Share"
                >
                  ↗
                </button>

                <button
                  className="icon-only-btn danger"
                  onClick={(e) => deleteSession(e, s.id)}
                  title="Delete"
                >
                  🗑
                </button>
              </div>
            </div>
))}
        </div>
      </div>

      <div className="main-area">
        <div className="scroll-region">
          <div className="content-inner">
            <div className="app-header">
              <p>Talk to it, or ask it to research anything</p>
              <div className="badges">
                <span className="badge">Planner</span><span className="badge">Researcher</span>
                <span className="badge">Writer</span><span className="badge">Critic</span><span className="badge">Rodrik</span>
              </div>
            </div>

            <div className="pill-row">
              {SUGGESTIONS.map((s) => <button key={s} className="pill" onClick={() => sendMessage(s)}>{s}</button>)}
            </div>

            <div className="chat-window">
              {messages.map((m, i) => (
                <div key={i} className={"chat-bubble " + m.role}>
                  {m.isSteps ? (
                    <div className="checklist">
                      {m.steps.length === 0 && (
                        <div className="checklist-item active">
                          <span className="checklist-icon">◌</span>
                          <span>Starting...</span>
                        </div>
                      )}
                      {m.steps.map((s, si) => (
                        <div key={si} className={"checklist-item" + (si === m.steps.length - 1 ? " active" : " done")}>
                          <span className="checklist-icon">{si === m.steps.length - 1 ? "◌" : "✓"}</span>
                          <span>{s}</span>
                        </div>
                      ))}
                    </div>
                  ) : m.isHtml ? (
                    <div dangerouslySetInnerHTML={{ __html: m.content }} />
                  ) : (
                    <p>{m.content}</p>
                  )}
                  {m.image && <img className="report-image" src={`data:image/png;base64,${m.image}`} />}
                  {m.pdf && (
                    <a className="pdf-download" href={`data:application/pdf;base64,${m.pdf}`} download={`${(m.topic || "report").replace(/\s+/g, "_")}.pdf`}>
                      ⬇ Download PDF
                    </a>
                  )}
                  {!m.isSteps && (
                    <div className="msg-actions">
                      <button className="icon-only-btn" onClick={() => copyMessage(i, m.content, m.isHtml)} title="Copy">
                        {copiedIndex === i ? "✓" : "⧉"}
                      </button>
                      {m.role === "assistant" ? (
                        <>
                          <button
                            className={"icon-only-btn" + (reactions[i] === "up" ? " active" : "")}
                            onClick={() => toggleReaction(i, "up")}
                            title="Good response"
                          >👍</button>
                          <button
                            className={"icon-only-btn" + (reactions[i] === "down" ? " active" : "")}
                            onClick={() => toggleReaction(i, "down")}
                            title="Bad response"
                          >👎</button>
                          <button className="icon-only-btn" onClick={() => shareMessage(m.content, m.isHtml)} title="Share">↗</button>
                          <button className="icon-only-btn" onClick={() => regenerate(i)} title="Regenerate">↻</button>
                        </>
                      ) : (
                        <button className="icon-only-btn" onClick={() => shareMessage(m.content, false)} title="Share">↗</button>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={endRef}></div>
            </div>
          </div>
        </div>

        <div className="input-wrap">
          {attachedFile && (
            <div className="attach-chip">
              📎 {attachedFile.name}
              <button onClick={removeAttachment} title="Remove attachment">✕</button>
            </div>
          )}
          <div className="input-pill">
            <input type="file" ref={fileInputRef} style={{ display: "none" }} accept=".txt,.md" onChange={handleFileSelected} />
            <button className="pill-icon-btn" onClick={handleAttachClick} title="Attach a file">＋</button>
            <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder="Ask Rodrik..." rows={1} />
            <button
              className={"pill-icon-btn" + (recording ? " recording" : "")}
              onClick={recording ? stopRecording : startRecording}
              title={recording ? "Stop recording" : "Speak instead"}
            >
              {recording ? "■" : "🎤"}
            </button>
            <button className="pill-icon-btn send" onClick={() => sendMessage()} title="Send">➤</button>
          </div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);