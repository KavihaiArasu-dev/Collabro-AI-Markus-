# Markus AI — README & Architecture

**One-sentence definition:** Markus AI is a modular, multimodal desktop
assistant that combines perception (voice, vision, screen), contextual
memory, planning, permission-gated tool execution, and a JARVIS-style
interaction model — with **OmniRoute** as a provider-agnostic AI gateway
instead of a single hard-coded LLM.

This document merges the original Markus-AI codebase (built earlier,
Gemini-only) with the deep-research architecture in
`Markus_AI_JARVIS_Architecture_Deep_Research.md`. It reflects what's
**already built**, what the research recommends **replacing**, and what's
still **planned**.

---

## 1. What changed: single-LLM → AI gateway

The original build called Gemini directly from `brain/gemini.py`. The
research's central recommendation is to stop hard-coding a provider:

> **Markus owns intelligence orchestration, context, planning, memory,
> permissions and tools. OmniRoute owns model/provider abstraction,
> routing and resilience.**

Concretely, Markus should talk to one OpenAI-compatible gateway endpoint
instead of embedding a provider SDK in the core assistant:

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

OmniRoute dashboard: `http://localhost:20128/dashboard`
Docs / provider catalog: https://omniroute.online/#providers

### Routing aliases → Markus modes

| Markus mode         | OmniRoute route |
|----------------------|------------------|
| Normal conversation  | `auto`           |
| Fast answer          | `/fast`          |
| Programming          | `/coding`        |
| Cost saving          | `/cheap`         |
| Local/private        | `/offline`       |
| Adaptive reasoning   | `/smart`         |

Provider/model names behind each alias are **dynamic** — Markus should
not assume `auto` always maps to the same underlying model.

### Provider tiers (for Markus's own routing policy, on top of OmniRoute)

- **Tier A — General intelligence** (complex reasoning, long context,
  architecture, hard coding, planning): Gemini, Claude, OpenAI,
  DeepSeek, Mistral, Qwen — selected dynamically via OmniRoute, not
  hard-coded.
- **Tier B — Fast intelligence** (short answers, intent classification,
  quick tool decisions): Groq, Cerebras.
- **Tier C — Local intelligence** (private/offline/dev/testing): Ollama,
  LM Studio, vLLM.

---

## 2. Current implementation status

| Piece | Status | Notes |
|---|---|---|
| `config.py`, `main.py` | ✅ Built | `config.py` now also holds all `OMNIROUTE_*` settings |
| `ai/omniroute_health.py` | ✅ Built | Distinguishes ONLINE / OFFLINE / STARTING / ERROR / AUTHENTICATION_ERROR / PROVIDER_ERROR — sync + async |
| `ai/omniroute_manager.py` | ✅ Built | detect → start → wait → connect, with a startup lock to prevent duplicate `omniroute serve` processes |
| `ai/omniroute_client.py` | ✅ Built | OpenAI-compatible client that calls `ensure_running()` before every request; routes by mode (`normal`/`fast`/`coding`/`cheap`/`offline`/`smart`), not hard-coded model names |
| `server.py` + `api/system.py` | ✅ Built | FastAPI app; `GET /api/system/omniroute` (read-only poll) and `POST /api/system/omniroute/ensure` (active start/recover) |
| `brain/gemini.py` | ⚠️ Superseded | Kept for now as a fallback path; `Router`/agents should prefer `ai/omniroute_client.py` |
| `brain/router.py` | ⚠️ Partial | Has intent classification + dispatch; still needs to become the full **Model Router** (task_type/privacy/latency/complexity → OmniRoute route) — `ai/omniroute_client.py`'s `route` param is the first piece of this |
| `brain/memory.py` (SQLite) | ⚠️ Minimal | Works, but research recommends a proper vector store (ChromaDB) and memory *categories* (see §5) |
| `brain/commands.py` | ✅ Built | Already matches the research's Rule 2/3 (deterministic parsing before any LLM/tool call — see §6) |
| `speech/vad.py` | ✅ Built | Standalone voice activity detection, previously inlined in `Listener` — see §7 |
| `speech/conversation_state.py` | ✅ Built | IDLE→...→SPEAKING state machine, wake-word cooldown, continuous-conversation mode — see §7 |
| `speech/` (wakeword, whisper, tts, listener) | ✅ Built | Matches recommended Voice Pipeline (§7) closely; `wakeword.py` now uses the cooldown from `conversation_state.py` |
| `vision/face_tracking.py` | ✅ Built | Periodic detection + centroid tracking between frames — see §7 |
| `vision/` (camera, face, gesture, emotion, pose, object) | ✅ Built | Matches recommended Vision Pipeline (§7); screen OCR still missing |
| `brain/perception.py` | ✅ Built | Fuses audio+vision into one `PerceptionContext`, privacy-gated by `MICROPHONE_ENABLED`/`CAMERA_ENABLED`/`EMOTION_DETECTION_ENABLED`; expression is always phrased as a hedged estimate, never a fact — see §7 |
| `automation/` (apps, browser, keyboard, system) | ✅ Built | Maps to the research's `tools/` layer; needs the risk-level/permission wrapper (§6) |
| Permission Manager | ❌ Not built | New — see §6 |
| Context Manager | ⚠️ Partial | `brain/perception.py` covers the audio/vision half; still needs app-state/screen context merged in — see §4 |
| HUD (PySide6) | ❌ Not built | New — Markus is currently CLI/voice-loop only |
| Screen intelligence / OCR | ❌ Not built | New |
| Multi-agent architecture | ❌ Not built | Future phase, not needed for v1 |

Tests already written (`tests/`) continue to apply: the command parser,
memory, and router logic don't change shape, they just gain an
OmniRoute-backed model layer underneath. `tests/test_omniroute.py` (13
tests) covers the OmniRoute health checker, manager, and status route;
`tests/test_vad.py`, `tests/test_conversation_state.py`,
`tests/test_face_tracking.py`, and `tests/test_perception.py` (33 tests
combined) cover the perception layer — all mocked/synthetic, no real
gateway, microphone, or camera needed. 66 tests total.

### Running the OmniRoute layer

```bash
cp .env.example .env      # fill in OMNIROUTE_API_KEY if your gateway needs one
pip install -r requirements.txt --break-system-packages

# start OmniRoute yourself once, OR let Markus try to start it
# (OMNIROUTE_AUTO_START=true, requires `omniroute` on PATH):
omniroute serve

uvicorn server:app --reload --port 8000
curl http://127.0.0.1:8000/api/system/omniroute
```

If `omniroute` isn't on PATH, `ai/omniroute_manager.py` logs a clear error
and reports `ERROR` status instead of crashing — it never leaves Markus in
an unclear state.

### Privacy defaults for the perception layer

`MICROPHONE_ENABLED=true` and `WAKE_WORD_ENABLED=true` by default;
`CAMERA_ENABLED=false` and `EMOTION_DETECTION_ENABLED=false` by default —
vision stays off until explicitly turned on. Set
`LOCAL_PROCESSING_ONLY=true` (default) to keep speech/vision inference on
this machine. `RAW_AUDIO_RETENTION`, `RAW_VIDEO_RETENTION`, and
`EMOTION_HISTORY` all default to `false` — turning them on is a deliberate
opt-in, not a side effect of enabling a feature. See `.env.example`.

---

## 3. Target high-level architecture

```text
User
  |
  +--> Voice ----------------------+
  +--> Camera ---------------------+
  +--> Screen / OCR ---------------+
  +--> Keyboard / GUI -------------+
                                   |
                                   v
                         +----------------------+
                         |   Markus Context     |
                         |      Manager         |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |  Intent Classifier   |
                         |  Planner             |
                         |  Permission Manager  |
                         |  Model Router        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      OmniRoute       |
                         |   AI Gateway Layer   |
                         +----------+-----------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
       Gemini                    Claude                    OpenAI
       Groq                     Cerebras                 DeepSeek
       Qwen                     Mistral                   Ollama
          +-------------------------+-------------------------+
                                    |
                                    v
                         Markus response / plan
                                    |
              +---------------------+----------------------+
              |                     |                      |
             TTS                  HUD                  Tools
              |                     |                      |
          Edge-TTS               PySide6              PyAutoGUI
```

### Ownership split (Markus vs. OmniRoute)

| Layer | Markus | OmniRoute |
|---|---|---|
| Conversation, context, planning | Yes | No |
| Memory | Yes | Optional gateway memory |
| Tool selection & permissions | Yes | Gateway guardrails can supplement |
| Model selection *policy* | Yes | Provider-level routing |
| Provider fallback / health | Consume/observe | Yes |
| Multi-provider API | No | Yes |
| Desktop automation, voice, vision, HUD | Yes | No |

```text
MARKUS    = Assistant Operating System
OMNIROUTE = AI Model Gateway
LLMs      = Intelligence Providers
TOOLS     = Action Layer
MEMORY    = Long-Term Context
PYTHON    = Deterministic Execution Layer
PYSIDE6   = User Interface
```

---

## 4. Core modules (new)

### Context Manager
Combines voice/vision/screen input, active app, current task, current
user, and retrieved memory into one structured input for the model:

```json
{
  "user": "current_user",
  "active_app": "VS Code",
  "screen_state": "coding",
  "voice_input": "fix this authentication error",
  "recent_actions": [],
  "memory": [],
  "permissions": { "file_write": true, "terminal": true }
}
```

### Intent Classifier
Categories: `CHAT, QUESTION, SEARCH, CODE, DEBUG, FILE_OPERATION,
APP_CONTROL, SYSTEM_CONTROL, BROWSER_AUTOMATION, VISION, OCR, REMINDER,
TASK_MANAGEMENT, EMAIL, CALENDAR, SECURITY, LOCAL_AI, MULTI_STEP_ACTION`.
(The current `brain/router.py` already implements a smaller version of
this — `chat, code, image, vision, automation, system`.)

### Planner
Turns a high-level request into ordered, executable steps and **never
executes actions directly** — it hands steps to the Permission Manager
and Tool Router.

```text
User: "Create a React project called Markus Dashboard."
Planner:
1. Validate destination folder.
2. Check Node.js availability.
3. Create project.
4. Install dependencies.
5. Open project in VS Code.
6. Verify the development server.
7. Report result.
```

### Model Router (Markus-level policy, sits above OmniRoute)

```python
class MarkusModelRouter:
    async def generate(self, messages, task_type, privacy="normal",
                        latency="balanced", complexity="normal"):
        if privacy == "local":
            route = "/offline"
        elif task_type == "coding":
            route = "/coding"
        elif latency == "fast":
            route = "/fast"
        elif complexity == "high":
            route = "/smart"
        else:
            route = "auto"
        # call OmniRoute with `route`
```

Model registry (avoid hard-coding providers anywhere else in the app):

```python
MODEL_PROFILES = {
    "normal":  {"route": "auto"},
    "fast":    {"route": "/fast"},
    "coding":  {"route": "/coding"},
    "cheap":   {"route": "/cheap"},
    "offline": {"route": "/offline"},
    "smart":   {"route": "/smart"},
}
```

---

## 5. Memory architecture

Current build uses SQLite for conversation turns + a flat facts table.
The research recommends layering it:

```text
                 MEMORY
                    |
       +------------+------------+
       |            |            |
   Short-term   Episodic     Semantic
     Memory       Memory       Memory
       |            |            |
  Current task   Past events   Knowledge
       |            |            |
       +------------+------------+
                    |
                    v
              Vector Store (ChromaDB)
```

- **Short-term:** current conversation, current task, recent tool
  outputs, current screen context.
- **Episodic:** completed tasks, user interactions, important events.
- **Preference:** UI/coding preferences, frequently used apps, preferred
  languages/workflows.
- **Project:** current projects, repo context, architecture decisions,
  known bugs.

**Memory safety:** don't save everything. Tag every write with a
category (`TEMPORARY, SESSION, PREFERENCE, PROJECT, IMPORTANT`) and
require explicit policy approval before persisting anything sensitive.

```python
memory.save(category="PROJECT", content="Markus frontend uses React and Tailwind")
```

Migration path: keep `brain/memory.py`'s SQLite table for short-term/
episodic rows (cheap, already works, already tested), and add a
`memory/chroma.py` layer for semantic/preference retrieval once
conversation history is large enough to need vector search.

---

## 6. Permission Manager & Tool Router (new — closes the biggest gap)

**Architectural rule:** an LLM response alone must never authorize a
destructive action.

```text
LLM → Planner → Permission Manager → Tool Router → OS
```

*(Not: `LLM → shell` directly.)*

### Permission defaults

| Action | Default |
|---|---|
| Read files | Allow |
| Search web | Allow |
| Open application | Allow |
| Type text | Ask for sensitive contexts |
| Delete file | Confirm |
| Execute shell command | Confirm |
| Install software | Confirm |
| Change system settings | Confirm |
| Send email | Confirm |
| Upload data | Confirm |
| Access camera / microphone | User-controlled |

### Tool risk model

- **LOW:** read file, search web, open application
- **MEDIUM:** write file, run dev command, change app settings
- **HIGH:** delete file, destructive shell command, send email, upload
  private data, change security settings — must require confirmation.

### Tool Router

```python
class ToolRouter:
    async def execute(self, tool_name, arguments):
        ...
```

Tool namespace (target set — current `automation/` covers `system.*` and
part of `browser.*` already):

```text
system.open_app        browser.search      files.read      terminal.run
system.close_app       browser.open        files.write     git.status
system.get_status      browser.navigate    files.search    git.diff
                                            files.move      git.commit
vision.capture   vision.analyze   calendar.list   calendar.create
email.search     email.draft      email.send
```

Every tool definition should carry: `name, description, arguments,
permissions, risk_level, timeout, rollback`.

**Note:** `brain/commands.py` already follows Rule 2/3 from the
research — it parses automation requests deterministically and calls
straight into `automation/`, without asking the LLM whether to act.
Wrapping it with explicit `risk_level` + confirmation prompts is the
next step, not a rebuild.

---

## 7. Voice & vision pipelines (mostly already built)

**Voice** (matches `speech/` closely):

```text
Microphone → VAD → Wake Word ("Hey Markus") → Faster-Whisper → Text
→ Context Manager → LLM / OmniRoute → Response → Edge-TTS → Speaker
```

The wake-word detector stays independent from the LLM — already true in
`speech/wakeword.py`.

**Status: perception layer built.** On top of the existing `speech/` and
`vision/` packages:

- `speech/vad.py` — standalone voice activity detection (previously
  inlined in `Listener.record_utterance`), tunable via
  `VAD_SILENCE_TIMEOUT` / `VAD_MIN_SPEECH_DURATION` /
  `VAD_MAX_RECORDING_DURATION` / `VAD_SILENCE_THRESHOLD`.
- `speech/conversation_state.py` — the `IDLE → ACTIVATED → LISTENING →
  TRANSCRIBING → PROCESSING → RESPONDING → SPEAKING → IDLE` state machine,
  plus wake-word cooldown (`WAKE_WORD_COOLDOWN`) and continuous-conversation
  mode (`CONTINUOUS_CONVERSATION`, `CONTINUOUS_CONVERSATION_TIMEOUT`) so a
  follow-up turn doesn't need to repeat the wake word.
- `vision/face_tracking.py` — a `FaceTracker` that runs full face
  detection every `FACE_TRACKING_REDETECT_EVERY_N_FRAMES` frames and
  cheap centroid tracking in between, instead of paying detection cost
  every frame.
- `brain/perception.py` — fuses audio + vision into one
  `PerceptionContext`, privacy-gated by `MICROPHONE_ENABLED` /
  `CAMERA_ENABLED` / `EMOTION_DETECTION_ENABLED` (disabling a capability
  means updates to it are silently dropped, not just hidden in the UI).
  `to_prompt_context()` always phrases expression as a hedged estimate
  ("appears happy, confidence 72%"), never as an assertion about the
  user's actual emotional state.

Covered by `tests/test_vad.py`, `tests/test_conversation_state.py`,
`tests/test_face_tracking.py`, and `tests/test_perception.py` (33 tests,
all synthetic/mocked — no real microphone or camera needed).

**Vision** (matches `vision/` closely): never stream raw video to the
LLM — process locally, emit structured events instead.

```json
{ "event": "person_detected", "identity": "authorized_user", "confidence": 0.94, "location": "desk" }
```

**Screen intelligence (still not built):** OCR + UI detection → structured
state → Context Manager, instead of sending screenshots to the model:

```json
{ "application": "VS Code", "window_title": "login.tsx", "visible_error": "401 Unauthorized", "language": "TypeScript" }
```

---

## 8. Streaming & HUD states (new)

For a JARVIS-like feel, don't wait for the full response before showing
activity — stream tokens to the HUD text and to a TTS sentence buffer
simultaneously.

Recommended state machine: `LISTENING → THINKING → PLANNING → EXECUTING
→ SPEAKING → WAITING_FOR_CONFIRMATION → ERROR → IDLE`.

HUD is PySide6-based and does not exist yet in the current build
(main.py is currently a text/voice CLI loop).

---

## 9. Recommended project structure (target)

```text
markus-ai/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── core/            context_manager.py, intent_classifier.py, planner.py,
│   │                     model_router.py, response_generator.py, event_bus.py
│   ├── ai/               omniroute_client.py, model_registry.py,
│   │                     routing_policy.py, streaming.py
│   ├── voice/            wake_word.py, stt.py, tts.py
│   ├── vision/           camera.py, face.py, gesture.py,
│   │                     object_detection.py, screen_ocr.py
│   ├── memory/           chroma.py, retrieval.py, preferences.py, episodic.py
│   ├── tools/             router.py, browser.py, files.py, terminal.py,
│   │                     applications.py, git.py
│   ├── security/          permissions.py, authentication.py, secrets.py
│   └── hud/               main_window.py, status_panel.py,
│                         activity_panel.py, overlay.py
├── tests/
├── data/
├── logs/
├── models/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

**Mapping from the current flat layout:** `speech/` → `app/voice/`,
`vision/` → `app/vision/` (+ new `screen_ocr.py`), `brain/router.py` →
splits into `app/core/{intent_classifier,planner,model_router}.py`,
`brain/gemini.py` → replaced by `app/ai/omniroute_client.py`,
`brain/memory.py` → `app/memory/` (SQLite short-term + new Chroma
layer), `automation/` → `app/tools/`, `brain/commands.py` logic → folds
into `app/tools/router.py` + `app/security/permissions.py`. This is a
restructuring, not a rewrite — the working logic moves, it doesn't need
to be re-derived.

---

## 10. Development phases (revised, replaces the original plan's phases)

- **Phase 1 — Core:** PySide6 shell, Context Manager, OmniRoute
  connection, basic chat, streaming, model routing.
- **Phase 2 — Voice:** wake word, Faster-Whisper, Edge-TTS, interruption,
  speech-state HUD. *(Mostly done — port existing `speech/` code.)*
- **Phase 3 — Tools:** app launcher, file ops, terminal, browser, Git,
  Permission Manager. *(Automation mostly done — add Permission Manager.)*
- **Phase 4 — Memory:** ChromaDB, conversation/preference/project memory,
  retrieval. *(SQLite short-term memory done — add vector layer.)*
- **Phase 5 — Vision:** camera, face, gesture, YOLO, OCR, screen
  understanding. *(Mostly done — add screen OCR.)*
- **Phase 6 — Agent architecture:** planner, supervisor/coding/research/
  vision/automation agents, multi-agent communication. *(Future.)*
- **Phase 7 — Production:** security hardening, structured logs,
  provider health, failure recovery, performance, automated tests,
  packaging. *(Tests already started — 20 passing.)*

---

## 11. Architectural rules

1. **Do not couple Markus to one LLM.** Talk to OmniRoute, not a
   provider SDK, directly in business logic.
2. **LLMs should not directly control the OS.** `LLM → Planner →
   Permission Manager → Tool Router → OS`, never `LLM → shell`.
3. **Use deterministic tools for deterministic work.** Open app →
   subprocess; read file → filesystem API; git status → Git CLI; system
   metrics → psutil. Don't ask an LLM to do what normal software already
   does reliably. *(`brain/commands.py` already follows this.)*
4. **Keep provider abstraction outside business logic.** Say "give me a
   coding-capable response," not "call Gemini model X."
5. **Treat provider availability as dynamic.** Discover current models
   from OmniRoute rather than assuming the catalog is permanent.

### OmniRoute caveats to keep in mind

Verify provider terms/auth before relying on them; verify model
capabilities before sending vision/audio/tool calls; don't assume
identical context sizes or function-calling behavior across providers;
monitor latency/error rates; keep a local fallback for critical
workflows; test fallback behavior before depending on it; protect
OmniRoute dashboard/API credentials; keep destructive OS actions behind
Markus's own permission layer regardless of what the gateway allows.

---

## 12. Minimum viable next step

Don't build every JARVIS feature at once. Progress so far:

1. ✅ **Done.** `ai/omniroute_client.py` (OpenAI-compatible client hitting
   OmniRoute) exists alongside `brain/gemini.py`, plus the full
   detect/start/wait/connect lifecycle (`ai/omniroute_manager.py`), a
   health checker that distinguishes offline/auth/provider errors
   (`ai/omniroute_health.py`), and a status API (`server.py` +
   `api/system.py`) — see "Running the OmniRoute layer" in §2.
2. Add a minimal Context Manager (a dict, not a class hierarchy yet)
   feeding `Router.handle()`.
3. Wrap `brain/commands.py` results with a risk level and a
   confirm-before-HIGH-risk-actions check — this is the Permission
   Manager MVP.
4. Wire `brain/router.py` to call `ai/omniroute_client.py` (via the
   `route` parameter) instead of `brain/gemini.py`, so the intent
   classification and chat handlers actually go through OmniRoute.
5. Everything else (HUD, ChromaDB, screen OCR, multi-agent) is a later
   phase and shouldn't block this step.

---

## 13. Sources

- OmniRoute: https://omniroute.online/#providers ·
  https://omniroute.online/ · https://github.com/blessedalways/omniroute
- JARVIS-1 (multimodal agent memory/planning research):
  https://arxiv.org/abs/2311.05997
- Personalized AI Assistant via Personal KV-Cache Retrieval:
  https://arxiv.org/abs/2510.22765
- Mark Zuckerberg's 2016 JARVIS project (WIRED):
  https://www.wired.com/story/mark-zuckerberg-jarvis-ai/
- Original source document: `Markus AI - JARVIS Inspired Features & System Design`
