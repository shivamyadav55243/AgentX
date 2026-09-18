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
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);

  async function refreshSessions() {
    const res = await fetch("/api/sessions");
    setSessions(await res.json());
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
    setHistoryOpen(false);
    refreshSessions();
  }

  async function loadSession(id) {
    const res = await fetch(`/api/sessions/${id}`);
    const data = await res.json();
    setSessionId(id);
    setMessages(rebuildMessages(data.messages));
    setHistoryOpen(false);
  }

  async function sendMessage(text) {
    const content = (text || input).trim();
    if (!content || !sessionId) return;

    setMessages((prev) => [...prev, { role: "user", content }]);
    setInput("");
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

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  return (
    <div className="app-shell">
      <button className={"history-toggle" + (historyOpen ? " open" : "")} onClick={() => setHistoryOpen(!historyOpen)} title="Toggle history">
        <span className="toggle-icon">☰</span>
      </button>

      <div className={"history-panel" + (historyOpen ? " open" : "")}>
        <button className="new-chat-btn" onClick={startNewChat}>+ New chat</button>
        <h4>Chats</h4>
        <div className="history-list">
          {sessions.length === 0 && <p className="muted">No chats yet.</p>}
          {sessions.map((s) => (
            <button
              key={s.id}
              className={"history-item" + (s.id === sessionId ? " active" : "")}
              onClick={() => loadSession(s.id)}
            >
              <span className="history-label">{s.title}</span>
              <span className="history-time">{s.updated}</span>
            </button>
          ))}
        </div>
      </div>

      <div className={"main-area" + (historyOpen ? " shifted" : "")}>
        <header className="app-header">
          <h1>AgentX</h1>
          <p>Talk to it, or ask it to research anything</p>
          <div className="badges">
            <span className="badge">Planner</span><span className="badge">Researcher</span>
            <span className="badge">Writer</span><span className="badge">Critic</span><span className="badge">Rodrik</span>
          </div>
        </header>

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
            </div>
          ))}
          <div ref={endRef}></div>
        </div>

        <div className="input-row">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="Ask me anything, or say 'research ...' for a full report" rows={1} />
          <button className="send-btn" onClick={() => sendMessage()}>➤</button>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);