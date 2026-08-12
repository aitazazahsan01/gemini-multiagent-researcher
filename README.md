# 🔬 Gemini Multi-Agent Researcher

A **production-style, stateful multi-agent research pipeline** built with [LangGraph](https://github.com/langchain-ai/langgraph) and Google Gemini. Four specialized AI agents collaborate through a stateful graph, with two human-in-the-loop checkpoints and an automatic self-correction loop — all streamed live to a web UI.

---

## ✨ Features

- 🧠 **Multi-Agent Architecture** — Planner, Researcher, Writer, and Critic agents working in a coordinated pipeline
- 🔁 **Self-Correction Loop** — The Critic automatically sends the Writer back for revisions (up to 3 times) before surfacing the draft to a human
- 👤 **Human-in-the-Loop** — Two interrupt checkpoints let you approve or override the plan and final report
- 🌐 **Live Web UI** — Real-time streaming via Server-Sent Events (SSE) with a dark-mode interface
- 🔍 **Free Web Search** — Powered by DuckDuckGo (no API key required)
- 💾 **Stateful Execution** — Graph state persisted via `MemorySaver`, resumable mid-run
- ⚡ **FastAPI Backend** — Lightweight streaming API server

---

## 🏗️ Architecture

```
START
  │
  ▼
planner ──────────► breaks the topic into 3–5 focused sub-questions
  │
  ▼
human_plan_review ─► INTERRUPT: approve the plan or rewrite it
  │
  ▼
researcher ────────► DuckDuckGo search per sub-question, summarized with citations
  │
  ▼
writer ─────────────► drafts a report from all research notes
  │
  ▼
critic ─────────────► approved? ──yes──► human_final_review ──approve──► END
  │no                                        │
  └──────────────◄─ writer (revise) ◄────────┤ needs more work
                                             │
                                         INTERRUPT: approve or give feedback
```

### Agents

| Agent | Role |
|---|---|
| **Planner** | Breaks the user's topic into 3–5 focused, non-overlapping research sub-questions using Gemini structured output |
| **Human Plan Review** | Pauses execution — you can approve the plan or replace it with your own questions |
| **Researcher** | Runs a DuckDuckGo search per sub-question and uses Gemini to summarize results with `[n]` citations |
| **Writer** | Synthesizes all research notes into a fully cited report; rewrites using critic and/or human feedback |
| **Critic** | Strict structured-output judge: evaluates factual consistency, citation quality, and completeness |
| **Human Final Review** | Second interrupt — approve to finish, or send feedback for another revision pass |

---

## 🧩 Key LangGraph Concepts

| Concept | Usage |
|---|---|
| `StateGraph` + `TypedDict` | Shared state dict threaded through every node |
| Reducers (`operator.add`) | `research_notes` field appends across calls instead of being overwritten |
| `add_conditional_edges` | Powers the critic → writer self-correction loop |
| `interrupt()` / `Command(resume=...)` | Human-in-the-loop pause/resume at two checkpoints |
| `MemorySaver` | Required for interrupts; persists state per `thread_id` between calls |
| `with_structured_output(Pydantic)` | Forces LLM to return validated schemas (used by Planner and Critic) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- A free Google AI API key — [get one here](https://aistudio.google.com/apikey)

### Setup

```powershell
# 1. Clone the repo
git clone https://github.com/aitazazahsan01/gemini-multiagent-researcher.git
cd gemini-multiagent-researcher

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
copy .env.example .env
```

Edit `.env` with your Gemini API key:

```env
GOOGLE_API_KEY=AIza...
GOOGLE_MODEL=gemini-2.0-flash
```

> **Tip:** If a model gives a 404, list available models for your key:
> ```python
> python -c "from google import genai; import os; from dotenv import load_dotenv; load_dotenv(); [print(m.name) for m in genai.Client(api_key=os.environ['GOOGLE_API_KEY']).models.list()]"
> ```
> Then update `GOOGLE_MODEL` in `.env` — no code changes needed.

---

## 🖥️ Running the App

### Option 1: Interactive CLI

```powershell
python main.py
```

You'll be prompted for a topic, then dropped into the plan-review checkpoint and eventually the final-review checkpoint. Type `approve` to accept, or enter your own feedback.

### Option 2: Web UI (recommended)

```powershell
python -m uvicorn server:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser. The interface streams node-by-node progress in real time.

---

## 📁 Project Structure

```
gemini-multiagent-researcher/
├── agents.py          # All six agent node implementations
├── graph.py           # LangGraph StateGraph construction & conditional routing
├── state.py           # ResearchState TypedDict with reducer annotations
├── tools.py           # DuckDuckGo search helper with retry logic
├── server.py          # FastAPI app with SSE streaming endpoints
├── main.py            # Interactive CLI runner
├── web/
│   ├── index.html     # Web UI layout and modals
│   ├── styles.css     # Dark-mode glassmorphic stylesheet
│   └── app.js         # SSE event handling and markdown rendering
├── requirements.txt
└── .env.example
```

---

## 🛠️ API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/stream/start?topic=<your topic>` | `GET` | Start a new research run, returns an SSE stream |
| `/api/stream/resume?thread_id=<id>&value=<response>` | `GET` | Resume a paused graph from a human interrupt |

### SSE Event Types

| Event | Payload |
|---|---|
| `session` | `{ thread_id }` — unique ID for this run |
| `node` | `{ node, state }` — partial state update from the latest node |
| `interrupt` | `{ reason, topic/draft, instructions }` — human checkpoint fired |
| `done` | `{ state }` — graph completed, full final state |
| `error` | `{ message }` — something went wrong |

---

## 💡 Things Worth Trying

- **Lower `MAX_REVISIONS`** in `graph.py` to `1` and watch the critic get overruled by the cap
- **Override the plan** at `human_plan_review` with your own semicolon-separated sub-questions
- **Reject the final draft** to trigger another writer pass with your custom feedback
- **Swap `MemorySaver`** for `SqliteSaver` (`langgraph-checkpoint-sqlite`) so runs survive a server restart

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini (via `langchain-google-genai`) |
| Orchestration | LangGraph (`StateGraph`, `MemorySaver`) |
| Web Search | DuckDuckGo Search (`ddgs`) |
| API Server | FastAPI + Uvicorn |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Config | `python-dotenv` |

---

## 📄 License

MIT License — feel free to fork, modify, and use for your own projects.
