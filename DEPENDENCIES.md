# MARKUS AI — Dependency Overview

Two install targets: **backend** (`requirements.txt`, Python) and
**frontend** (`package.json`, Node). Grouped by the subsystem each package
serves, per `MARKUS.md`.

## Backend (Python) — `pip install -r requirements.txt`

| Subsystem | Packages | Why |
|---|---|---|
| Web backend | `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `python-dotenv`, `python-multipart`, `websockets` | API server + streaming chat |
| AI Gateway | `openai`, `httpx`, `tenacity` | OmniRoute is OpenAI-compatible — one client, no per-provider SDKs; `tenacity` handles retry/fallback |
| Agents | `langchain`, `langgraph` | Tool-calling scaffolding and multi-agent graph orchestration (Planner → Coder → Reviewer...) |
| RAG | `chromadb`, `faiss-cpu`, `sentence-transformers`, `pypdf`, `python-docx`, `unstructured` | Vector storage + embeddings + document parsing for the Knowledge Base |
| Databases | `sqlalchemy`, `alembic`, `asyncpg`, `psycopg2-binary`, `redis` | PostgreSQL (projects/users), SQLite-compatible ORM, Redis (cache/queues/sessions) |
| Auth & security | `python-jose`, `passlib`, `cryptography` | JWT sessions, password hashing, encrypted secrets at rest |
| Voice | `sounddevice`, `numpy`, `openwakeword`, `faster-whisper`, `soundfile`, `edge-tts` | Mic capture → wake word → local STT → TTS |
| Vision | `opencv-python`, `mediapipe`, `face-recognition`, `ultralytics`, `fer`, `pytesseract`, `pillow` | Camera, gesture/pose, face ID, object detection, emotion, screen OCR |
| Automation | `pyautogui`, `selenium`, `psutil`, `pygetwindow` | Desktop control, browser control, process/system info |
| Logging/utils | `loguru`, `pyyaml` | Structured logs, config files |
| Testing | `pytest`, `pytest-asyncio` | Test suite (async FastAPI routes + sync modules) |

Notes:
- `mediapipe` is pinned to `0.10.14` — newer builds dropped the legacy
  `solutions.hands`/`solutions.pose` API used by the gesture/pose modules.
- `pyautogui` needs a real display; it raises `KeyError('DISPLAY')` at
  import time on headless Linux — the codebase already catches this and
  degrades gracefully (see the earlier Markus-AI scaffold's README).
- `langchain`/`langgraph` are optional scaffolding, not required to call
  OmniRoute directly — drop them if you'd rather hand-roll agent
  orchestration around the `openai` client.

## Frontend (Node) — `npm install`

| Subsystem | Packages | Why |
|---|---|---|
| Framework | `react`, `react-dom`, `react-router-dom`, `vite`, `typescript`, `@vitejs/plugin-react` | App shell, routing, build tooling |
| Styling | `tailwindcss`, `postcss`, `autoprefixer`, `tailwindcss-animate`, `clsx`, `tailwind-merge`, `class-variance-authority` | Design system (glassmorphism, gradients, states from `MARKUS.md`) |
| Motion / orb | `framer-motion`, `gsap`, `three`, `@react-three/fiber`, `@react-three/drei`, `@studio-freight/lenis` | AI Orb animation states, particle system, smooth scroll |
| UI components | `@radix-ui/*`, `lucide-react` | Accessible primitives (dialog, tabs, tooltip...) + icon set (design system says no emojis) |
| Chat / code | `react-markdown`, `remark-gfm`, `rehype-highlight`, `@monaco-editor/react` | Markdown rendering, syntax highlighting, integrated code editor |
| State / data | `zustand`, `axios`, `socket.io-client` | Client state, REST calls, WebSocket streaming from the backend |
| Auth | `better-auth` | Matches the auth choice in `MARKUS.md` §6/§8 |
| Types/lint | `@types/react`, `@types/react-dom`, `@types/three`, `eslint`, `eslint-plugin-react-hooks` | Dev-time only |

## What you don't need to install yourself

OmniRoute itself is a separate service (its own repo:
https://github.com/blessedalways/omniroute) — it's a dependency of the
*system*, not a pip/npm package. Run it separately and point
`OMNIROUTE_BASE_URL=http://localhost:20128/v1` at it; the `openai` package
above is the only thing the Python backend needs to talk to it.
