# Markus AI System Assistant (Full Plan) — OmniRoute Edition

*This is the architecture & design document — the system-level spec.
For a module-by-module capability catalog with build/test status, see
`SKILLS.md`. For the full Python + Node package lists, see
`DEPENDENCIES.md`.*

A local, privacy-first AI assistant ("Markus") that:

- Runs entirely on your own machine using a **local LLM**, with cloud APIs
  available when needed — local stays preferred, and provider selection is
  no longer hard-coded. Markus talks to **OmniRoute**, a multi-provider AI
  gateway, instead of calling one LLM SDK directly. See §6a.
- Accepts input via **voice** and **text chat**
- Uses **RAG (Retrieval-Augmented Generation)** to answer questions from your
  own documents/notes/knowledge base
- Can **control the local system** — open apps, run commands, manage files,
  check status — always through a **Permission Manager** and deterministic
  **Tool Router**, never by letting an LLM call the shell directly (§11).
- Responds back via **text-to-speech (TTS)**
- Wakes on a **wake word**, verifies it's **your voice**, then handles a command
- Has a **floating orb HUD** frontend — a plain HTML/CSS/JS page showing only a
  glowing, breathing orb, no text or buttons (see the full orb spec in Part 3)

Built in **TypeScript** using **Next.js** (`markus-next`) for the backend/API and
**React/Vite** for the frontend, structured as **Clean Architecture**. No Jupyter notebook anywhere
in the project.

---

## MARKUS AI — Intelligent Multi-Agent Development Platform

---

## 1. Overview

MARKUS AI is a modular AI Operating System designed for software development,
automation, research, and intelligent workflows.

Unlike traditional AI assistants, MARKUS is built around multiple specialized
AI agents that collaborate to complete complex tasks while maintaining a clean,
scalable architecture. Those agents no longer call one hard-coded LLM each —
every agent's model calls pass through **OmniRoute**, so the underlying
provider (local or cloud) can change without touching agent logic.

The platform is designed to be:

- Local-first with optional cloud integrations, routed dynamically rather than
  hard-coded
- Multi-Agent Architecture
- Developer-focused
- Extensible through plugins
- Privacy-conscious
- Production-ready
- Cross-platform

MARKUS combines:

- AI Agents
- Local & Cloud LLMs, unified behind one AI gateway (OmniRoute)
- RAG
- Automation
- Code Generation
- Project Management
- System Control
- Voice Interface
- Modern Dashboard

Everything follows Clean Architecture.

---

## 2. Core Vision

MARKUS is not just an AI chatbot.

It is an AI development operating system capable of:

- Building software
- Managing projects
- Writing code
- Reviewing code
- Running automations
- Understanding documentation
- Managing files
- Searching knowledge
- Coordinating AI agents
- Helping developers from idea to deployment

**Ownership principle (new):** Markus owns intelligence orchestration,
context, planning, memory, permissions, and tools. OmniRoute owns
model/provider abstraction, routing, and resilience. Markus is the
operating system; OmniRoute is the model gateway underneath it.

```text
MARKUS    = Assistant Operating System
OMNIROUTE = AI Model Gateway
LLMs      = Intelligence Providers
AGENTS    = Specialized Reasoning Units
TOOLS     = Action Layer
MEMORY    = Long-Term Context
PYTHON    = Deterministic Execution Layer
```

---

## 3. Design Principles

## Single Source of Truth

This MARKUS.md file defines the complete project architecture.

The implementation must always match this document.

---

## Modular

Every feature exists as an independent module.

No unnecessary coupling.

---

## Extensible

New agents

New tools

New providers

New plugins

can be added without modifying existing modules. New LLM providers in
particular should require **zero code changes** — they're added to
OmniRoute's provider catalog, not to Markus.

---

## Multi-Agent Collaboration

Instead of one AI,

MARKUS uses multiple specialized agents.

Each agent performs a dedicated responsibility, and each agent's model calls
go through the same Model Router → OmniRoute path (§6a), so different agents
can be tuned to different routing policies (e.g. the Coder agent defaults to
`/coding`, the Debug agent defaults to `/smart`) without duplicating provider
code.

---

## Local First

Every major feature should work locally.

Cloud APIs are optional enhancements, reached through OmniRoute's `/offline`
vs. `auto`/`/smart` routes rather than a separate code path per provider.

---

## Security First

Sensitive operations require confirmation.

Permissions are role-based.

Actions are logged.

An LLM's response, on its own, is never sufficient authorization for a
destructive action — see the Permission Manager in §11.

---

## 4. High Level Architecture

```text
                    +------------------------+
| MARKUS UI |
                    +-----------+------------+
|  |
                 REST API / WebSocket
|  |
          +---------------------+----------------------+
|  |
   Agent Orchestrator                         System Services
|  |
 +--------+---------+----------------------+-----------+
| --- | --- |
Coder          Researcher            Architect
|  |
Reviewer
|  |
Debugger
|  |
Planner
|  |
Automation
|  |
Memory
|  |
RAG
|  |
Context Manager          <- NEW: merges voice/vision/screen/app state + memory
|  |
Intent Classifier         <- NEW: CHAT / CODE / DEBUG / SYSTEM_CONTROL / ...
|  |
Permission Manager        <- NEW: allow / ask / block, before any tool runs
|  |
Model Router               <- NEW: task_type/privacy/latency/complexity -> route
|  |
OmniRoute (AI Gateway)      <- NEW: replaces direct "LLM Router" to one SDK
| --- | --- |
Gemini   Claude    OpenAI
Groq     Cerebras  DeepSeek
Qwen     Mistral   Ollama / LM Studio / vLLM
|  |
Tool Registry / Tool Router
|  |
Infrastructure
```

The previous single "LLM Router" step is now two steps: a Markus-owned
**Model Router** that decides *what kind* of model capability is needed
(coding, fast, cheap, offline, smart), and **OmniRoute**, which decides
*which actual provider* serves that request and handles fallback if a
provider is down. See §6a for the full detail and code pattern.

---

## 5. AI Agent Ecosystem

## Markus Core

Coordinates every agent.

Responsibilities

- task routing
- workflow planning
- agent communication
- conflict resolution
- **model routing policy** — deciding which OmniRoute route (`auto`,
  `/fast`, `/coding`, `/cheap`, `/offline`, `/smart`) each agent's request
  should use, based on task type, privacy, latency, and complexity (§6a)

---

## Architect Agent

Creates

- project architecture
- folder structures
- API design
- database design

Default routing: `/smart` (high-complexity reasoning).

---

## Coder Agent

Responsible for

- implementation
- refactoring
- optimization

Supports

Python

TypeScript

JavaScript

React

Next.js

Node

Rust

Go

Java

and more.

Default routing: `/coding`.

---

## Reviewer Agent

Performs

- code review
- security review
- performance review
- style review
- architecture validation

Default routing: `/coding` or `/smart` for architecture-level reviews.

---

## Debug Agent

Finds

- bugs
- runtime errors
- stack traces
- memory leaks
- dependency issues

Default routing: `/smart`.

---

## Research Agent

Searches

- documentation
- libraries
- APIs
- best practices
- release notes

Default routing: `auto`, escalating to `/smart` for synthesis across many
sources.

---

## Documentation Agent

Generates

README

API docs

Architecture docs

Technical reports

Developer guides

Default routing: `auto`.

---

## UI/UX Agent

Designs

- interfaces
- design systems
- components
- accessibility
- user flows

Default routing: `auto`.

---

## Automation Agent

Executes

- scheduled tasks
- CI/CD workflows
- repetitive developer actions

Automation Agent output never reaches the OS directly — every action passes
through the Permission Manager and Tool Router (§11), following:

```text
LLM -> Planner -> Permission Manager -> Tool Router -> OS
```

not `LLM -> shell`.

Default routing: `/fast` for command interpretation (this agent should
rarely need a large reasoning model — deterministic tools do the actual
work, per the architectural rule in §11a).

---

## Memory Agent

Maintains

- conversations
- project context
- coding style
- architecture knowledge

Memory is now layered, not a single flat store (see §6b for the full
breakdown): **short-term** (current task, recent tool outputs), **episodic**
(completed tasks, events), **preference** (coding style, favorite tools),
and **project** (repo context, architecture decisions, known bugs). All are
backed by RAG/vector storage (ChromaDB/FAISS, per §6 tech stack) with a
memory-category tag (`TEMPORARY, SESSION, PREFERENCE, PROJECT, IMPORTANT`)
so nothing sensitive is persisted without explicit policy approval.

---

## 6. Technology Stack

Frontend

- React
- TailwindCSS
- Vite
- TypeScript

Backend

- Python
- FastAPI

AI Gateway (new)

- **OmniRoute** — one OpenAI-compatible endpoint in front of every provider
  below; handles routing, automatic fallback, and health monitoring so
  Markus doesn't embed provider SDKs directly. See §6a.

AI Providers (reached through OmniRoute, not called directly)

- Ollama / LM Studio / vLLM — local, privacy-preserving, offline-capable
- OpenAI
- Claude
- Gemini
- DeepSeek
- Groq
- Cerebras
- Qwen
- Mistral

RAG

- ChromaDB
- FAISS

Embeddings

- Sentence Transformers

Database

- PostgreSQL
- SQLite
- Redis

Authentication

- Better Auth

Cloud

- AWS
- Docker

---

## 6a. AI Gateway — OmniRoute Integration (new)

**Status: reference implementation built.** `ai/omniroute_health.py`
(status detection), `ai/omniroute_manager.py` (detect → start → wait →
connect, with a startup lock), `ai/omniroute_client.py` (routed
OpenAI-compatible client), and `server.py` + `api/system.py` (the
`GET /api/system/omniroute` / `POST /api/system/omniroute/ensure` status
API) exist in the Markus-AI codebase and are covered by
`tests/test_omniroute.py` (13 tests, gateway mocked out). See that
project's `README.md` §2 for how to run it. The Windows auto-start step
(Task Scheduler / startup shortcut running `omniroute serve`) is still a
manual setup step, not something Markus's Python code can configure for
you.

The old plan called Gemini (or another provider) directly from application
code. That coupling is removed. Markus now talks to one gateway endpoint:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:20128/v1",
    api_key="YOUR_OMNIROUTE_KEY",
)

response = client.chat.completions.create(
    model="auto",  # an OmniRoute routing alias, not a hard-coded model name
    messages=[
        {"role": "system", "content": "You are Markus, a desktop AI assistant."},
        {"role": "user", "content": "Explain this error."},
    ],
)
```

- Gateway endpoint: `http://localhost:20128/v1`
- Local dashboard: `http://localhost:20128/dashboard`
- Provider catalog / docs: <https://omniroute.online/#providers>

### Routing aliases → Markus modes

| Markus mode | OmniRoute route |
| --- | --- |
| Normal conversation | `auto` |
| Fast answer | `/fast` |
| Programming | `/coding` |
| Cost saving | `/cheap` |
| Local/private | `/offline` |
| Adaptive reasoning | `/smart` |

The provider behind each alias is dynamic — Markus should never assume
`auto` always resolves to the same underlying model, and should discover
current models/capabilities from OmniRoute rather than assuming the catalog
is permanent.

### Provider tiers (Markus's own routing policy, on top of OmniRoute)

- **Tier A — General intelligence:** Gemini, Claude, OpenAI, DeepSeek,
  Mistral, Qwen — for complex reasoning, long context, architecture, hard
  coding, planning.
- **Tier B — Fast intelligence:** Groq, Cerebras — for short answers, intent
  classification, quick tool decisions, UI commands.
- **Tier C — Local intelligence:** Ollama, LM Studio, vLLM — for private
  requests, offline operation, sensitive local context, dev/testing.

### Model Router (Markus-level policy layer)

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

### Model registry

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

### Ownership split

| Layer | Markus | OmniRoute |
| --- | --- | --- |
| Conversation, context, planning | Yes | No |
| Memory | Yes | Optional gateway memory |
| Tool selection & permissions | Yes | Gateway guardrails can supplement |
| Model selection *policy* | Yes | Provider-level routing |
| Provider fallback / health | Consume/observe | Yes |
| Multi-provider API | No | Yes |
| Desktop automation, voice, vision, HUD | Yes | No |

### Caveats

Verify provider terms/auth before relying on them; verify model
capabilities before sending vision/audio/tool calls; don't assume identical
context sizes or function-calling behavior across providers; monitor
latency/error rates; keep a local fallback for critical workflows; test
fallback behavior before depending on it; protect OmniRoute
dashboard/API credentials; keep destructive OS actions behind Markus's own
permission layer regardless of what the gateway allows.

---

## 6b. Memory Architecture (expanded)

```text
                 MEMORY
|  |
       +------------+------------+
| --- | --- |
   Short-term   Episodic     Semantic
     Memory       Memory       Memory
| --- | --- |
  Current task   Past events   Knowledge
| --- | --- |
       +------------+------------+
|  |
                    v
           Vector Store (ChromaDB/FAISS)
```

- **Short-term:** current conversation, current task, recent tool outputs,
  current screen/app context.
- **Episodic:** completed tasks, user interactions, important events.
- **Preference:** UI/coding preferences, frequently used apps, preferred
  languages/workflows.
- **Project:** current projects, repo context, architecture decisions,
  known bugs.

**Memory safety:** don't save everything. Tag every write with a category
(`TEMPORARY, SESSION, PREFERENCE, PROJECT, IMPORTANT`) and require explicit
policy approval before persisting anything sensitive.

```python
memory.save(category="PROJECT", content="Markus frontend uses React and Tailwind")
```

---

## 6c. Perception Layer — Speech, Wake Word & Facial Emotion (new)

**Status: reference implementation built.** `speech/vad.py`,
`speech/conversation_state.py`, `vision/face_tracking.py`, and
`brain/perception.py` exist in the Markus-AI codebase, covered by 33
tests (`tests/test_vad.py`, `tests/test_conversation_state.py`,
`tests/test_face_tracking.py`, `tests/test_perception.py`) — all
synthetic/mocked, no real microphone or camera required to run them.

### Design principle: three independent perception systems

```text
                MARKUS PERCEPTION
|  |
        +--------------+--------------+
        v              v              v
      AUDIO          SPEECH          VISION
| --- | --- |
        v              v              v
   Wake Word          STT       Face Detection
| --- | --- |
        +--------------+--------------+
                       v
                Context Manager
|  |
                       v
                  Markus AI
```

Microphone, speech recognition, and camera logic are not tightly
coupled — each is a separate service, and all three feed the same
Context Manager rather than calling each other directly.

### Wake word state machine

```text
IDLE -> ACTIVATED -> LISTENING -> TRANSCRIBING -> PROCESSING
     -> RESPONDING -> SPEAKING -> IDLE          (ERROR reachable from most states)
```

Built as `speech/conversation_state.py`'s `ConversationStateMachine`,
with only the listed transitions legal — an illegal jump (e.g. straight
from `IDLE` to `SPEAKING`) raises `InvalidTransitionError` rather than
silently producing a confusing HUD state.

**False-activation prevention:** a cooldown (`WAKE_WORD_COOLDOWN`, default
1500ms) ignores repeat wake-word detections right after one fires, and
**continuous conversation mode** (`CONTINUOUS_CONVERSATION`,
`CONTINUOUS_CONVERSATION_TIMEOUT`, default 8000ms) lets a follow-up turn
skip the wake word entirely if it arrives soon enough after the previous
one ended.

### Voice activity detection

`speech/vad.py`'s `VoiceActivityDetector` replaces a fixed silence
threshold with configurable RMS-energy detection
(`VAD_SILENCE_THRESHOLD`), a silence timeout that ends an utterance
(`VAD_SILENCE_TIMEOUT`), a minimum-speech-duration floor that discards
noise/clicks that never had real speech (`VAD_MIN_SPEECH_DURATION`), and
a hard cap (`VAD_MAX_RECORDING_DURATION`) so a stuck-open mic can't
record forever.

### Face detection vs. tracking

Per the "don't run full detection on every frame" principle,
`vision/face_tracking.py`'s `FaceTracker` runs full detection every
`FACE_TRACKING_REDETECT_EVERY_N_FRAMES` frames (default 10) and reuses
centroid-matched tracks in between — cutting CPU/GPU cost without
losing per-face identity across frames.

### Facial expression — estimate, not fact

Expression output is always treated as a model prediction with a
confidence score, never a definitive read of someone's internal state:

```text
DO:      "Expression estimate: happy — 72%"
DO NOT:  "The user is happy."
```

`brain/perception.py`'s `PerceptionContext.to_prompt_context()` bakes
this in — it renders expression as `"Visible facial expression appears
{expr} (confidence {conf}%) — treat this as a rough signal, not a
confirmed emotional state,"` and there is no code path that asserts an
emotion as fact.

### Multimodal context fusion

```text
{
  "audio": { "wakeWordDetected": true, "speaking": false, "transcript": "..." },
  "vision": { "facePresent": true, "faceCount": 1, "expression": "neutral", "expressionConfidence": 0.81 }
}
```

`PerceptionManager` builds this from whatever audio/vision state is
currently available and hands the resulting `PerceptionContext` to
`brain/router.py` before it builds a prompt. Camera raw frames are never
passed to the model — only this structured summary (mirrors the "don't
send raw video to the LLM" rule for screen intelligence in §6a).

### Privacy is enforced, not just displayed

Every capability is gated by a config flag, and disabling one means
updates to it are dropped rather than merely hidden in a UI:

| Flag | Default | Effect when off |
| --- | --- | --- |
| `MICROPHONE_ENABLED` | `true` | `update_audio()` calls are ignored |
| `CAMERA_ENABLED` | `false` | `update_vision()` calls are ignored |
| `EMOTION_DETECTION_ENABLED` | `false` | Expression fields stay empty even if a face is present — presence isn't consent for expression analysis |
| `LOCAL_PROCESSING_ONLY` | `true` | Keeps speech/vision inference on-device |
| `RAW_AUDIO_RETENTION` / `RAW_VIDEO_RETENTION` / `EMOTION_HISTORY` | `false` | Nothing sensitive persists unless explicitly turned on |

Vision (camera + emotion) defaults to **off** — it has to be turned on
deliberately, unlike microphone/wake-word which default to on.

### Error handling and graceful degradation

Each perception input fails independently: a missing microphone disables
voice mode but keeps text chat; a missing wake-word model falls back to
push-to-talk; a missing camera disables vision but voice/text continue
normally — matching the existing pattern already used throughout
`speech/` and `vision/` (see `README.md`'s "Notes" section for the
mediapipe/pyautogui examples of this same principle).

---

## 7. Project Structure

```text
markus/

├── apps/
│
├── frontend/
│
├── backend/
│
├── agents/
│
├── application/
│
├── domain/
│
├── core/                     <- NEW: context_manager.py, intent_classifier.py,
│                                 planner.py, model_router.py, event_bus.py
│
├── ai/                        <- NEW: omniroute_client.py, model_registry.py,
│                                 routing_policy.py, streaming.py
│
├── security/                  <- NEW: permissions.py, authentication.py, secrets.py
│
├── infrastructure/
│
├── adapters/
│
├── plugins/
│
├── tools/
│
├── memory/
│
├── rag/
│
├── workflows/
│
├── docs/
│
├── tests/
│
├── config/
│
├── scripts/
│
└── main.py
```

The three new top-level folders (`core/`, `ai/`, `security/`) are the direct
result of splitting the old single "LLM Router" responsibility into Context
Manager + Intent Classifier + Planner + Model Router (`core/`), the
OmniRoute client itself (`ai/`), and the Permission Manager (`security/`).
Nothing existing needs to move — `agents/`, `tools/`, `memory/`, `rag/`,
`workflows/`, and the Clean Architecture layers (`application/`, `domain/`,
`infrastructure/`, `adapters/`) are unchanged.

---

## 8. Core Modules

## Authentication

- Login
- OAuth
- Better Auth
- Sessions
- Roles

---

## AI Chat

- Multi-model support, routed through OmniRoute rather than one hard-coded
  provider
- Streaming
- Vision
- File uploads
- Conversations

---

## Agent Workspace

Manage

- running agents
- task queues
- execution history
- **per-agent routing policy** — which OmniRoute route each agent defaults
  to (§5), visible and adjustable from the workspace

---

## Projects

Create

Open

Clone

Import

Manage

---

## Code Editor

Integrated editor

Diff viewer

Syntax highlighting

Terminal

---

## Knowledge Base

Upload

PDF

Markdown

Word

Text

Code repositories

---

## Plugin Marketplace

Third-party extensions

Agent extensions

Developer tools

---

## Workflow Builder

Visual automation

Task chains

Conditional execution

Triggers

---

## 9. APIs

/api/chat

/api/agents

/api/projects

/api/workflows

/api/plugins

/api/files

/api/auth

/api/search

/api/rag

/api/settings

/api/models — **new**: exposes the current OmniRoute routing aliases and
their live provider/model resolution, instead of a static provider list

---

## 10. Agent Communication

Every agent communicates using structured messages.

```text
Task
  ↓
Planner
  ↓
Architect
  ↓
Coder
  ↓
Reviewer
  ↓
Debugger
  ↓
Result
```

Each arrow above that involves a model call now resolves through the
Context Manager → Intent Classifier → Model Router → OmniRoute chain
described in §4 and §6a, rather than each agent calling its own LLM client.

---

## 11. Security

Permission system

Encrypted secrets

Audit logs

Role management

Sandbox execution

Confirmation before destructive actions

---

## 11a. Permission Manager & Tool Router (expanded)

**Architectural rule:** an LLM response alone must never authorize a
destructive action.

```text
LLM → Planner → Permission Manager → Tool Router → OS
```

*(Not: `LLM → shell` directly.)*

### Permission defaults

| Action | Default |
| --- | --- |
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

Every tool definition carries: `name, description, arguments, permissions,
risk_level, timeout, rollback`.

### Five architectural rules (apply everywhere in Markus)

1. **Do not couple Markus to one LLM.** Talk to OmniRoute, not a provider
   SDK, directly in business logic.
2. **LLMs should not directly control the OS.** Always
   `LLM → Planner → Permission Manager → Tool Router → OS`.
3. **Use deterministic tools for deterministic work.** Open app →
   subprocess; read file → filesystem API; git status → Git CLI; system
   metrics → psutil. Don't ask an LLM to do what normal software already
   does reliably.
4. **Keep provider abstraction outside business logic.** Say "give me a
   coding-capable response," not "call Gemini model X."
5. **Treat provider availability as dynamic.** Discover current models
   from OmniRoute rather than assuming the catalog is permanent.

---

## 12. Roadmap

Phase 1

Core Chat

Project Management

Authentication

**OmniRoute gateway connection** (new — replaces "pick one LLM SDK" as the
Phase 1 AI dependency)

---

Phase 2

Multi-Agent System

Memory (layered: short-term/episodic/preference/project — §6b)

RAG

Plugins

**Permission Manager MVP** (new)

---

Phase 3

Automation

Voice Assistant

Desktop App

**Screen intelligence / OCR** (new)

---

Phase 4

Cloud Sync

Mobile App

Marketplace

Enterprise Features

**Multi-agent supervisor architecture, provider health dashboards** (new)

---

## 13. Future Features

- AI Pair Programming
- Autonomous Software Teams
- Figma Integration
- GitHub Automation
- Jira Integration
- Slack Integration
- VS Code Extension
- CLI
- Mobile Companion
- Browser Extension

---

## 14. Guiding Principles

MARKUS should always be:

- Modular
- Maintainable
- Extensible
- Secure
- Fast
- Offline-capable
- Developer-first
- AI-native
- **Provider-agnostic** (new — no feature should assume one specific LLM)

Every architectural decision should support these principles.

---

## 15. Sources (new)

- OmniRoute: <https://omniroute.online/#providers> ·
  <https://omniroute.online/> · https://github.com/blessedalways/omniroute
- JARVIS-1 (multimodal agent memory/planning research):
  <https://arxiv.org/abs/2311.05997>
- Personalized AI Assistant via Personal KV-Cache Retrieval:
  <https://arxiv.org/abs/2510.22765>
- Mark Zuckerberg's 2016 JARVIS project (WIRED):
  <https://www.wired.com/story/mark-zuckerberg-jarvis-ai/>

---

## MARKUS AI — UI/UX Design System & Visual Guidelines

*(Unchanged from the original plan — the OmniRoute update is a backend/AI-gateway
change and does not alter the visual design system below. One addition: the
AI States in §6 below now include `PLANNING`, `EXECUTING`, and
`WAITING_FOR_CONFIRMATION`, to visually reflect the new Permission Manager
step — see the note at the end of that section.)*

---

## 1. Design Philosophy

MARKUS AI is not a chatbot.

MARKUS is an **AI Operating System** built for developers, engineers, researchers, and creators.

The interface should communicate:

- Intelligence
- Precision
- Speed
- Elegance
- Trust
- Innovation

The UI should feel like a combination of:

- Apple VisionOS
- Linear
- Raycast
- GitHub Copilot
- Arc Browser

Avoid excessive cyberpunk styling or cluttered HUD designs. Every animation should have purpose.

---

## 2. Design Principles

## Minimal

Remove visual noise.

Only display information when needed.

---

## Context Aware

The interface should react to what Markus is currently doing.

Examples:

- Thinking
- Coding
- Researching
- Reviewing
- Speaking

---

## Motion Driven

Animations should provide feedback.

Never animate simply for decoration.

---

## Premium

Every interaction should feel polished.

Soft shadows.

Smooth transitions.

High frame rates.

No sudden movements.

---

## 3. Theme

Primary Theme

AI Operating System

Mood

- Modern
- Intelligent
- Calm
- Professional
- Premium

---

## 4. Color Palette

## Background Colors

Primary Background

`#05070D`

Secondary Background

`#0B1020`

Surface

`#111827`

Card Background

rgba(255,255,255,0.04)

Glass Background

rgba(255,255,255,0.06)

---

## Text Colors

Primary

`#FFFFFF`

Secondary

`#B8C2CC`

Muted

`#7B8794`

Disabled

`#5C6773`

---

## Primary AI Colors

Cyan

`#00E5FF`

Blue

`#3B82F6`

Purple

`#8B5CF6`

Emerald

`#10B981`

Orange

`#FF8A00`

Amber

`#FACC15`

Copper (new — orb circuit-trace accent, see §7 reference visual language)

`#D89B5C`

Red

`#EF4444`

White

`#FFFFFF`

---

## 5. Gradient System

Primary Gradient

`#00E5FF`

↓

`#3B82F6`

↓

`#8B5CF6`

---

Secondary Gradient

`#00FFF0`

↓

`#00A3FF`

↓

`#6D5BFF`

---

Success Gradient

`#10B981`

↓

`#22C55E`

---

Warning Gradient

`#FACC15`

↓

`#F59E0B`

---

Danger Gradient

`#FF4D6D`

↓

`#EF4444`

---

## 6. AI States

## Idle

Color

Cyan

Animation

Slow breathing

Glow

Low

Particles

Floating

---

## Listening

Color

Blue

Animation

Expanding ripple

Pulse speed

Medium

Particles

Moving inward

---

## Thinking

Color

Purple

Animation

Rotating rings

Particle vortex

Glow intensity

High

---

## Planning (new)

Color

Indigo

Animation

Nodes assembling into a path

Purpose

Visualizes the Planner (§10/§11a in the platform doc) breaking a request
into steps before any tool runs

---

## Coding

Color

Orange

Animation

Streaming lines

Digital particles

Fast pulse

---

## Research

Color

Indigo

Animation

Orbiting nodes

Connection lines

---

## Executing (new)

Color

Blue → Orange gradient

Animation

Progress ring filling per step

Purpose

Visualizes the Tool Router actually running a permitted action

---

## Waiting for Confirmation (new)

Color

Amber

Animation

Slow pulse, orb pauses mid-motion

Purpose

Visualizes the Permission Manager blocking on a HIGH-risk action (§11a)
until the user confirms

---

## Speaking

Color

Emerald

Animation

Audio waves

Equalizer bars

Soft pulse

---

## Success

Color

Green

Animation

Single expanding pulse

---

## Warning

Color

Amber

Animation

Slow blinking

---

## Error

Color

Red

Animation

Glitch

Shake

Red pulse

---

## 7. AI Orb

The AI Orb represents Markus.

It is the heart of the interface.

### Reference visual language (from concept art)

Five reference renders define the target look. Key motifs to carry into
implementation, observed directly from the references:

- **Organic, not perfectly circular, outer boundary.** The outermost
  ring reads like a wobbly cell membrane or coastline, not a precise
  circle — irregular radius, slightly rough edge, built from dense
  particle/dot texture rather than a clean stroke.
- **Concentric ring "shell."** Multiple nested rings/bands between the
  outer boundary and the core, at varying opacity and thickness — some
  segmented into tick-marks (like a dial or iris), some smooth glass.
  This shell is what gives the orb depth rather than reading as a flat
  circle.
- **Glowing core, off-center is allowed.** The innermost light source is
  the brightest point and doesn't have to be dead-center — a couple of
  references have the core or an inner accent ring sitting slightly
  off-axis, which reads as more alive than perfect radial symmetry.
- **Sacred-geometry inner pattern at rest.** A flower-of-life /
  overlapping-circles lattice sits inside the innermost sphere in the
  idle-adjacent reference — use this as the **Idle** or **Thinking**
  state's inner detail, not something visible at all times.
- **Two distinct "energetic" treatments for active states:**
  - *Radiating spokes:* straight light rays fanning out from the core
    through the rings to the edge — reads as focused, directional
    energy. Good fit for **Executing** or **Responding**.
  - *Flow-field / vortex:* curved, wind-swept streaks spiraling into
    the core — reads as processing/synthesis. Good fit for **Thinking**
    or **Processing**.
- **Circuit-trace overlay in the warm accent.** One reference overlays
  amber/copper circuit-board-style traces (right-angle-ish wandering
  lines, not smooth curves) across the glass rings, breaking the
  cyan-only palette. Reserve this treatment for **Coding** — it's the
  one state where a second, warmer hue is justified, echoing the
  existing Orange = Coding assignment in §6 below.
- **Translucent glass, not solid fill.** Rings read as glass/energy
  shells you can partially see through to the ones behind — layer with
  low opacity + soft blur, not flat opaque strokes.
- **Fine particle dust, not sparkle.** Particles sit mostly along the
  outer ring as a soft grainy texture, not scattered decoratively across
  the whole canvas — keep the particle system (§9) concentrated near
  the shell boundary for this look, with a light scatter beyond it.

### Layers

```text
Outer Glow
   ↓
Particle Halo (dense near the shell boundary, sparse beyond it)
   ↓
Organic Outer Ring (irregular radius, dot/particle texture)
   ↓
Energy Ring Shell (2-4 nested translucent rings, some tick-marked)
   ↓
Glass Layer
   ↓
Core Reactor
   ↓
Inner Pulse
   ↓
Center Light (brightest point; may sit slightly off-center)
```

Idle/Thinking-only inner layer: a flower-of-life geometric lattice,
faint, inside the innermost sphere — fades in/out rather than being
permanently present, so it reads as a detail you notice rather than
visual clutter in every state.

---

### Animations

**Idle** — breathing (slow scale pulse on the whole shell); sacred-geometry
lattice faintly visible at the core.

**Listening** — ripple waves emanating outward from the core through the
ring shell.

**Thinking** — rotating energy; flow-field/vortex streaks curving into
the core (see "flow-field" reference above); geometric lattice visible.

**Planning** — nodes assembling into a path across the ring shell.

**Coding** — spinning hexagon; amber/copper circuit-trace lines overlaid
on the glass rings (see "circuit-trace" reference above) — the one state
that breaks from pure cyan.

**Research** — orbiting particles.

**Executing** — filling progress ring; radiating spokes fanning outward
from the core (see "radiating spokes" reference above).

**Waiting for Confirmation** — paused amber pulse; motion visibly stops
rather than continuing to animate, so "waiting" reads as a pause, not
just a color change.

**Speaking** — audio waveform; core pulses in sync with amplitude.

**Success** — green pulse, single expansion outward through the shell.

**Error** — glitch effect; shell briefly desyncs/jitters before settling.

---

## 8. Background Effects

Background should never be static.

Use

- radial gradients

- floating particles

- neural network

- moving stars

- soft noise

Opacity

2%–5%

Never distract the user.

---

## 9. Particle System

Particles

Count

300–500

Random

- size

- speed

- opacity

- direction

Behavior

Idle

Float

Thinking

Swirl

Coding

Move horizontally

Speaking

React to waveform

---

## 10. Neural Network

Animated nodes connected by glowing lines.

Nodes

Small circles

Connections

Animated

Fade

Reconnect

Disconnect

Purpose

Represent Markus' intelligence.

---

## 11. Sidebar

Collapsed

Icons only

Expanded

Icons

Labels

Search

Sections

Dashboard

Chat

Agents

Projects

Knowledge

Plugins

Workflow

Terminal

Settings

Hover

Expand smoothly

---

## 12. Dashboard

Cards

CPU

RAM

GPU

LLM

**Active Route** (new — shows the live OmniRoute alias/provider currently
in use, e.g. "auto → Gemini 2.5 Flash")

Latency

Memory

Projects

Active Agents

Recent Tasks

All cards

Glass

Rounded

Animated

---

## 13. Multi-Agent View

Each agent has its own card.

Planner

Architect

Researcher

Coder

Reviewer

Debugger

Automation

Memory

Each card displays

Status

Current task

Progress

Latency

Memory usage

**Routing policy** (new — which OmniRoute alias this agent is currently
using, per §5's per-agent defaults)

Active agent glows.

Inactive agents remain dim.

---

## 14. Workflow Visualization

Display execution flow.

Idea

↓

Planner

↓

Architect

↓

Research

↓

Coder

↓

Reviewer

↓

Debugger

↓

Deploy

Completed nodes

Green

Current node

Purple Glow

Upcoming

Gray

---

## 15. Chat Interface

Use clean layouts.

Avoid traditional chat bubbles.

Messages

Large spacing

Markdown support

Syntax highlighting

Code actions

Copy

Run

Debug

Explain

Save

---

## 16. Typography

Headings

Space Grotesk

Alternative

Sora

Body

Inter

Code

JetBrains Mono

Numbers

Geist Mono

---

## 17. Iconography

Use

Lucide Icons

or

Phosphor Icons

No emojis.

---

## 18. Glassmorphism

Cards

Background

rgba(255,255,255,0.04)

Border

rgba(255,255,255,0.08)

Blur

30px

Radius

20px

---

## 19. Shadows

Soft Shadow

0 8px 30px rgba(0,0,0,.35)

Glow Shadow

0 0 40px rgba(0,229,255,.25)

Purple Glow

0 0 50px rgba(139,92,246,.25)

Green Glow

0 0 35px rgba(16,185,129,.30)

---

## 20. Micro Interactions

Buttons

Scale

1 → 1.05

Cards

Tilt

Glow

Icons

Rotate slightly

Orb

Follow mouse

Sidebar

Smooth expansion

Notifications

Fade

Slide

Glow

---

## 21. Sound Visualization

During speaking

Display

- equalizer bars

- waveform

- glowing pulses

Color

Emerald

---

## 22. Loading Experience

Replace

Loading...

With

Initializing Memory

Planning Task

Analyzing Context

Selecting Agent

**Resolving Route** (new — shown while the Model Router picks an OmniRoute
alias, before the request reaches a provider)

Generating Response

Reviewing Output

Each stage

Animated

Progressive

---

## 23. Cursor Effects

Cursor

Small glowing dot

Hover

Magnetic attraction

Orb

Follows cursor slightly

Buttons

Glow on hover

---

## 24. Recommended Animation Library

Framer Motion

GSAP

React Three Fiber

Three.js

Motion One

Lenis

---

## 25. UI Component Library

shadcn/ui

Magic UI

Aceternity UI

Radix UI

Tailwind CSS

---

## 26. Signature Markus Features

Living AI Core

A dynamic 3D orb that reacts to every AI state, including the new Planning,
Executing, and Waiting-for-Confirmation states.

---

Multi-Agent Pipeline

Visualize every active AI agent in real time, including which OmniRoute
route each one is currently using.

---

Knowledge Galaxy

Interactive graph connecting files, memories, projects, and conversations.

---

Project Command Center

Unified dashboard for repositories, AI tasks, builds, deployments, and workflows.

---

Developer Terminal Overlay

AI assistance integrated directly into the terminal.

---

Adaptive Ambient Lighting

Entire interface changes lighting and glow based on Markus' current activity.

---

## 27. UI Goals

Every interaction should feel

- Fast
- Smooth
- Intelligent
- Predictable
- Professional
- Premium

The user should always feel that Markus is actively thinking, collaborating, and assisting—not simply responding.
