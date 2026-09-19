# 🌾 AgentX — Autonomous Multi-Agent Research & Intelligence Platform

AgentX is a full-stack AI platform that automates end-to-end research: a coordinated team of AI agents plans, researches, writes, and fact-checks reports on any topic — all inside a single, unified chat interface that also handles casual conversation and on-demand image generation.

## ✨ Features

- **Multi-agent research pipeline** — a Planner agent breaks a topic into sub-questions, Researcher agents investigate each one in parallel using real-time web search, a Writer agent synthesizes everything into a structured report, and a Critic agent reviews it and triggers automatic revisions when needed.
- **Unified chat interface** — no separate modes. Type naturally, and an intent router automatically decides whether you want a full research report, an AI-generated image, or just a conversation with the built-in assistant, **Rodrik**.
- **Real web search & citations** — powered by the Tavily API, so reports are grounded in current information with linked sources, not just an LLM's training data.
- **AI-generated report images** — each report can include an AI-generated header illustration (Google's Gemini image model, with an automatic Hugging Face fallback).
- **Multi-provider LLM routing** — Groq is used as the primary provider for speed, with Google Gemini as an automatic fallback, all behind a single rate-limit-aware client.
- **PDF export** — every report can be downloaded as a formatted PDF.
- **Persistent chat sessions** — full conversation history is saved and restored automatically, with a Claude-style sliding sidebar to browse and switch between past chats.
- **Custom, hand-built UI** — a React + Flask frontend with a warm dark theme, smooth CSS transitions, and a live step-by-step progress checklist while research runs.

## 🧠 Architecture

```
User message
     │
     ▼
Intent Router (classifies: research / image / chat)
     │
     ├── research ──► Planner ──► Researcher(s) ──► Writer ──► Critic ──► Report + Image + PDF
     ├── image    ──► Image Generator (Nano Banana → Hugging Face fallback)
     └── chat     ──► Rodrik (conversational assistant)
```

All LLM calls flow through a single rate-limited client (`agents/llm.py`) that tries Groq first for speed and falls back to Gemini automatically if needed.



## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Frontend:** React (via CDN), vanilla CSS, Server-Sent Events for live streaming
- **LLM providers:** Groq (primary), Google Gemini (fallback + image generation)
- **Web search:** Tavily API
- **Image generation:** Google Gemini (Nano Banana) with Hugging Face Stable Diffusion fallback
- **Storage:** JSON-based local persistence for chat sessions and report history

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/shivamyadav55243/AgentX.git
cd AgentX
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your environment variables
Create a `.env` file in the project root:

GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
HF_TOKEN=your_huggingface_token


### 4. Run the app
```bash
python server.py
```
Then open `http://localhost:5000` in your browser.

## 📁 Project Structure

```
AgentX/
├── agents/
│   ├── llm.py          # Centralized rate-limited LLM client (Groq + Gemini)
│   ├── planner.py       # Breaks topics into sub-questions
│   ├── researcher.py    # Web search + summarization per sub-question
│   ├── writer.py        # Synthesizes findings into a report
│   ├── critic.py        # Fact-checks and requests revisions
│   ├── chatbot.py       # Rodrik, the conversational assistant
│   ├── router.py        # Classifies intent: research / image / chat
│   └── image_gen.py     # AI image generation (Nano Banana + HF fallback)
├── storage/
│   ├── memory.py        # Report persistence
│   ├── sessions.py      # Chat session persistence
│   └── pdf_export.py    # Markdown-to-PDF conversion
├── web/
│   ├── index.html
│   ├── app.jsx           # React frontend
│   └── style.css
├── orchestrator.py       # Coordinates the full agent pipeline
├── server.py              # Flask backend + API routes
└── requirements.txt
```


## 📝 License

This project was built as a personal learning project. Feel free to explore, fork, and adapt it.

## 👤 Author

**Shivam Yadav**

---

Built from scratch as a hands-on way to learn multi-agent AI systems, full-stack development, and API orchestration.
