# Markus AI — Architecture & System Guide

**One-sentence definition:** Markus AI is a modular, multimodal desktop assistant that combines perception (voice, vision, screen), contextual memory, planning, permission-gated tool execution, a sub-millisecond voice command fast-path, and a JARVIS-style interaction model — with **OmniRoute** as a provider-agnostic AI gateway instead of a single hard-coded LLM.

This document reflects the current production codebase, including the **OmniRoute** gateway layer, **Desktop Actions Suite**, **Voice Command Fast-Path**, **Multi-Agent Orchestrator**, **Biometric Face Recognition**, and the **React/Vite Glassmorphism Orb HUD**.

---

## 1. Core Architecture: Single-LLM to AI Gateway

The original build called Gemini directly from `brain/gemini.py`. Markus now decouples model execution by routing through **OmniRoute**:

> **Markus owns intelligence orchestration, context, planning, memory, permissions, and tools. OmniRoute owns model/provider abstraction, routing, and resilience.**

Markus interacts with an OpenAI-compatible gateway endpoint rather than embedding individual provider SDKs inside core business logic:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:20128/v1",
    api_key="YOUR_OMNIROUTE_KEY",
)

response = client.chat.completions.create(
    model="auto",  # OmniRoute routing alias, not a hard-coded model name
    messages=[
        {"role": "system", "content": "You are Markus, a desktop AI assistant."},
        {"role": "user", "content": "Explain this error."},
    ],
)
```

OmniRoute Dashboard: `<http://localhost:20128/dashboard>`  
Docs / Provider Catalog: [OmniRoute Providers](https://omniroute.online/#providers)

### Routing Aliases & Markus Modes

| Markus Mode          | OmniRoute Route | Target Use Case                          |
| -------------------- | --------------- | ---------------------------------------- |
| Normal conversation  | `auto`          | Balanced intelligence for general tasks  |
| Fast answer          | `/fast`         | Low-latency intent & simple responses    |
| Programming          | `/coding`       | Code generation, refactoring, debugging  |
| Cost saving          | `/cheap`        | High-volume background classification    |
| Local/private        | `/offline`      | Fully local processing (Ollama/vLLM)     |
| Adaptive reasoning   | `/smart`        | Complex multi-step reasoning & planning  |

Provider and model names behind each alias are **dynamic** — Markus does not assume `auto` or `/coding` always maps to a static underlying provider.

### Provider Tiers

- **Tier A — General Intelligence** (complex reasoning, long context, architecture, hard coding, planning): Gemini, Claude, OpenAI, DeepSeek, Mistral, Qwen — routed via OmniRoute.
- **Tier B — Fast Intelligence** (short answers, intent classification, quick tool decisions): Groq, Cerebras.
- **Tier C — Local Intelligence** (private/offline/dev/testing): Ollama, LM Studio, vLLM.

---

## 2. Current Implementation Status

| Component | Status | Implementation Details |
| --------- | ------ | ---------------------- |
| **OmniRoute Gateway** | ✅ Built | `ai/omniroute_client.py`, `ai/omniroute_manager.py`, `ai/omniroute_health.py` with auto-start, health checks, and fallbacks. |
| **Voice Command Fast-Path** | ✅ Built | `core/voice_command_processor.py` provides sub-millisecond regex execution for app control, volume, media, screenshots, and system telemetry without LLM latency. |
| **Desktop Actions Engine** | ✅ Built | `actions/` (`app_controller.py`, `system_monitor.py`, `system_settings.py`, `web_search.py`, `youtube_controller.py`) with cross-platform OS control. |
| **Multi-Agent Orchestrator** | ✅ Built | `agents/` (`orchestrator.py`, `base_agent.py`, `implementations.py`) with Coder, Architect, Reviewer, Debugger, Researcher, UI/UX, and Automation agents. |
| **Tool Router & Security** | ✅ Built | `tools/tool_router.py` with 25+ tools mapped to `security/permissions.py` (LOW, MEDIUM, HIGH, CRITICAL risk tiers). |
| **Context Manager** | ✅ Built | `core/context_manager.py` combines active application, window title, screen state, user session, and retrieved memory. |
| **Intent Classifier** | ✅ Built | `core/intent_classifier.py` supporting 18 intent categories including `APP_CONTROL`, `YOUTUBE`, `VOICE_COMMAND`, and `SYSTEM_CONTROL`. |
| **Perception Layer** | ✅ Built | `brain/perception.py`, `speech/vad.py`, `speech/conversation_state.py`, and `vision/face_tracking.py` fusing audio and vision telemetry. |
| **Face Recognition & Biometrics** | ✅ Built | `vision/face_recognition.py`, YuNet/SFace ONNX pipelines, and owner profile storage in `data/known_faces/profiles.json`. |
| **RAG & Memory** | ✅ Built | `rag/` (chunker, loader, retriever, vector store) and `memory/memory_manager.py` (SQLite + Chroma vector store). |
| **Glassmorphic Orb HUD** | ✅ Built | `apps/frontend/` (React, TypeScript, Vite, CSS) with interactive floating AI Orb, particle canvas, and WebSocket perception stream. |
| **Speech Pipeline** | ✅ Built | `speech/` with WebRTC VAD, Wake-Word detection ("Hey Markus"), Faster-Whisper STT, and Edge-TTS synthesis. |
| **Automated Test Suite** | ✅ Built | `tests/` with 27 unit tests covering VAD, conversation states, face tracking, perception, RAG, domain entities, and Jarvis action modules. |

---

## 3. High-Level System Architecture

```text
                                  User
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
      Voice                       Vision                     Text / GUI
   (Microphone)                  (Camera)                 (Chat / Web HUD)
        |                           |                           |
        v                           v                           v
     VAD / STT              Face & Screen Tracking         FastAPI / WS
        |                           |                           |
        +---------------------------+---------------------------+
                                    |
                                    v
                         +---------------------+
                         |   Context Manager   |
                         +----------+----------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
  (Fast Path: Direct Voice)                      (Cognitive Path: Reasoning)
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
| VoiceCommandProcessor |                       |   Intent Classifier   |
| (sub-ms regex match)  |                       |   Multi-Agent Planner |
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            |                                               v
            |                                   +-----------------------+
            |                                   |  OmniRoute AI Gateway |
            |                                   +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                         +---------------------+
                         | Permission Manager  |
                         | (LOW / MED / HIGH)  |
                         +----------+----------+
                                    |
                                    v
                         +---------------------+
                         |     Tool Router     |
                         |  (Desktop Actions)  |
                         +----------+----------+
                                    |
         +--------------------------+--------------------------+
         |                          |                          |
         v                          v                          v
    OS Automation             Web / YouTube               Audio / TTS
  (App/Window/Volume)       (Search & Playback)         (Edge-TTS Voice)
```

### Architectural Separation: Markus vs. OmniRoute

| Layer | Markus AI | OmniRoute Gateway |
| ----- | --------- | ----------------- |
| Conversation, Context, Planning | Yes | No |
| Long-term Memory & RAG | Yes | Optional Gateway Caching |
| Tool Dispatch & Permissions | Yes | Gateway Guardrails (supplement) |
| Model Selection Policy | Yes | Provider-level Routing |
| Provider Fallbacks & Health Checks | Consumes & Observes | Yes |
| Multi-Provider Unified API | No | Yes |
| Desktop Automation & Local Perception | Yes | No |

```text
MARKUS    = Multimodal Assistant Operating System
OMNIROUTE = Provider-Agnostic Model Gateway
LLMs      = Upstream Intelligence Providers
TOOLS     = Deterministic OS Action Layer
MEMORY    = SQLite + Vector Storage
FRONTEND  = React / TypeScript Glassmorphic HUD
```

---

## 4. Core Modules & Yesterday's Updates

### Voice Command Fast-Path (`core/voice_command_processor.py`)

For instant system automation, Markus implements a deterministic fast-path that bypasses LLM latency for common commands:

- `"open chrome"` → `app_controller.open_app("chrome")`
- `"close spotify"` → `app_controller.close_app("spotify")`
- `"mute"` / `"volume up"` → `system_settings.set_volume(...)`
- `"brightness 80%"` → `system_settings.set_brightness("set", 80)`
- `"take screenshot"` → `system_settings.take_screenshot()`
- `"play Bohemian Rhapsody on youtube"` → `youtube_controller.play(...)`
- `"what's my battery level"` → `system_monitor.get_battery()`

### Desktop Actions Suite (`actions/`)

- **`app_controller.py`**: Cross-platform application lifecycle (Windows `os.startfile`/PowerShell, macOS `open -a`, Linux `subprocess`). Includes 30+ aliases, fuzzy window title matching, and active window focusing.
- **`system_monitor.py`**: Real-time telemetry including CPU load, memory utilization, disk partitions, GPU metrics via GPUtil, battery level, network adapters, and top resource-consuming processes.
- **`system_settings.py`**: Native Windows/macOS volume control (via NirCmd/PowerShell/AppleScript), monitor brightness (via WMI/ScreenBrightness), multi-display screenshot capture, screen locking, and WiFi SSID scanning.
- **`web_search.py`**: DuckDuckGo search integration with fallback browser launching and news search capabilities.
- **`youtube_controller.py`**: Direct YouTube video query search and instant browser playback.

### Multi-Agent Orchestrator (`agents/orchestrator.py`)

Routes complex user tasks through specialized agents:

- **CoderAgent**: Software implementation, refactoring, and code analysis.
- **ArchitectAgent**: High-level system design and multi-step execution plans.
- **ReviewerAgent**: Code quality inspection and security auditing.
- **DebugAgent**: Exception tracing, root-cause debugging, and fix proposals.
- **ResearchAgent**: Web searches, technical documentation synthesis, and inquiry responses.
- **AutomationAgent**: Desktop system operations, file actions, and terminal tasks.
- **MemoryAgent**: Interaction recording and contextual profile updates.

### Context Manager (`core/context_manager.py`)

Aggregates real-time multimodal telemetry into a structured state object:

```json
{
  "user": "Kavihai Arasu (Owner)",
  "active_app": "Visual Studio Code",
  "screen_state": "coding",
  "voice_input": "Run the test suite",
  "recent_actions": ["git status", "file read"],
  "memory": ["Prefers Python and TypeScript", "Dark theme active"],
  "permissions": { "terminal": true, "file_write": true }
}
```

---

## 5. Security & Permission-Gated Tool Router

An LLM response **never** directly touches the host operating system. All actions flow through the Permission Manager:

```text
LLM / Fast-Path → Planner → Permission Manager → Tool Router → Host OS
```

### Permission Defaults & Risk Model

| Action Category | Default Policy | Risk Level |
| --------------- | -------------- | ---------- |
| Read files | Allow | LOW |
| Web & YouTube search | Allow | LOW |
| Open application | Allow | LOW |
| System telemetry & battery info | Allow | LOW |
| Write / modify file | Allow | MEDIUM |
| Run dev command | Allow | MEDIUM |
| Adjust volume / brightness | Allow | MEDIUM |
| Delete file / directory | Confirm | HIGH |
| Destructive shell command | Confirm | HIGH |
| Lock screen / system reboot | Confirm | HIGH |
| Install software | Confirm | HIGH |
| System shutdown | Confirm | CRITICAL |

Every registered tool in `tools/tool_router.py` specifies `name`, `description`, `parameters`, and `risk_level`.

---

## 6. Project Directory Layout

The `markus/` repository is organized cleanly according to Clean Architecture principles:

```text
markus/
├── actions/                 # Desktop automation (apps, monitor, settings, web, YouTube)
│   ├── app_controller.py
│   ├── system_monitor.py
│   ├── system_settings.py
│   ├── web_search.py
│   └── youtube_controller.py
├── adapters/                # External adapters (e.g. GitHub API)
├── agents/                  # Multi-agent implementations & Orchestrator
├── ai/                      # OmniRoute client, routing policy, model registry
├── application/             # FastAPI REST endpoints & WebSocket server
│   └── routes/              # Routes: chat, agents, system, speech, vision, etc.
├── apps/
│   └── frontend/            # React/Vite Glassmorphism Orb HUD & Dashboard
├── brain/                   # Perception fusion & assistant state
├── config/                  # Pydantic settings & system constants
├── core/                    # Context Manager, Intent Classifier, Planner, Voice Fast-Path
├── data/                    # Known faces, biometric profiles, vector embeddings, models
├── domain/                  # Domain entities & conversation state machine
├── infrastructure/          # Database persistence & storage
├── memory/                  # Short-term SQLite & long-term vector memory
├── plugins/                 # Extensible plugin system
├── rag/                     # RAG document loaders, chunkers, and retrievers
├── security/                # Permission Manager, secrets vault, authentication
├── speech/                  # WebRTC VAD, Wake-Word, Faster-Whisper STT, Edge-TTS
├── tests/                   # Pytest test suite (27 passing tests)
├── tools/                   # Permission-gated Tool Router
├── vision/                  # Camera, face detection, tracking, recognition, screen capture
├── workflows/               # Multi-step workflow engine
├── main.py                  # Server entry point
├── package.json             # Root workspace configuration
├── pyproject.toml           # Python build configuration
├── requirements.txt         # Production dependencies
└── README.md                # System documentation
```

---

## 7. Setup & Execution Guide

### 1. Prerequisites & Environment

- Python 3.11+
- Node.js 18+ (for frontend dashboard)
- Optional: NVIDIA GPU with CUDA for accelerated Whisper and computer vision

```powershell
# Clone and enter the markus directory
cd c:\Users\kavih\Desktop\Project\projects\Markus_AI\markus

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and set your credentials:

```bash
cp .env.example .env
```

Key environment configurations:

- `OMNIROUTE_BASE_URL=http://localhost:20128/v1`
- `OMNIROUTE_API_KEY=your_key_here`
- `MICROPHONE_ENABLED=true`
- `WAKE_WORD_ENABLED=true`
- `CAMERA_ENABLED=false` (enable when camera feed is desired)

### 3. Run Automated Tests

Verify that all modules and action bridges function properly:

```powershell
python -m pytest tests
```

### 4. Start the Application

Start the backend server:

```powershell
python main.py
```

In a separate terminal, launch the frontend HUD:

```powershell
cd apps\frontend
npm install
npm run dev
```

The Markus Dashboard and Voice/Vision HUD will be accessible at `<http://localhost:5173>`, connecting to the backend at `<ws://localhost:8000/ws>`.

---

## 8. Research & References

- [OmniRoute Documentation](https://omniroute.online/) · [GitHub](https://github.com/blessedalways/omniroute)
- [JARVIS-1: Open-World Multimodal Agent Memory & Planning](https://arxiv.org/abs/2311.05997)
- [Personalized AI Assistant via Personal KV-Cache Retrieval](https://arxiv.org/abs/2510.22765)
- [Mark Zuckerberg's 2016 JARVIS Project (WIRED)](https://www.wired.com/story/mark-zuckerberg-jarvis-ai/)
- Clean Architecture in Python & Multi-Agent Collaboration
