# Markus AI — Skills Catalog

This document catalogs Markus's capabilities one skill/module at a time:
what it does, which files implement it, its build status, its test
coverage, and the config that controls it. For the *system design*
behind these skills (diagrams, agent ecosystem, ownership model), see
`ARCHITECTURE.md`. For package lists, see `DEPENDENCIES.md`.

Status legend: ✅ Built · ⚠️ Partial/Superseded · ❌ Not built

---

## 1. AI Gateway (OmniRoute)

Markus talks to one OpenAI-compatible gateway endpoint instead of
embedding a provider SDK per model — see `ARCHITECTURE.md` §6a for the
full design.

| Module | Status | What it does |
| --- | --- | --- |
| `ai/omniroute_health.py` | ✅ Built | Distinguishes `ONLINE` / `OFFLINE` / `STARTING` / `ERROR` / `AUTHENTICATION_ERROR` / `PROVIDER_ERROR` — sync + async health checks against `GET /v1/models` |
| `ai/omniroute_manager.py` | ✅ Built | detect → start → wait → connect lifecycle; a startup lock prevents two concurrent callers from spawning duplicate `omniroute serve` processes; retries up to `OMNIROUTE_MAX_START_RETRIES` |
| `ai/omniroute_client.py` | ✅ Built | OpenAI-compatible client that calls `ensure_running()` before every request; routes by *mode* (`normal`/`fast`/`coding`/`cheap`/`offline`/`smart`) via `config.OMNIROUTE_ROUTES`, never a hard-coded model name |
| `server.py` + `api/system.py` | ✅ Built | FastAPI app; `GET /api/system/omniroute` (read-only poll, safe every few seconds) and `POST /api/system/omniroute/ensure` (actively starts/recovers) |
| `brain/gemini.py` | ⚠️ Superseded | Kept as a fallback path; new code should prefer `ai/omniroute_client.py` |

**Config:** `OMNIROUTE_HOST`, `OMNIROUTE_PORT`, `OMNIROUTE_BASE_URL`,
`OMNIROUTE_API_KEY` (server-side only — never expose to a browser build),
`OMNIROUTE_AUTO_START`, `OMNIROUTE_AUTO_RESTART`,
`OMNIROUTE_START_TIMEOUT`, `OMNIROUTE_HEALTH_INTERVAL`,
`OMNIROUTE_REQUEST_TIMEOUT`, `OMNIROUTE_MAX_START_RETRIES`.

**Tests:** `tests/test_omniroute.py` — 13 tests, all mocked (no real
gateway or `omniroute` CLI required).

**Run it:**

```bash
cp .env.example .env      # fill in OMNIROUTE_API_KEY if your gateway needs one
pip install -r requirements.txt --break-system-packages

omniroute serve            # or let Markus auto-start it (OMNIROUTE_AUTO_START=true)

uvicorn server:app --reload --port 8000
curl http://127.0.0.1:8000/api/system/omniroute
```

If `omniroute` isn't on PATH, the manager logs a clear error and reports
`ERROR` status instead of crashing.

---

## 2. Voice — Wake Word, VAD, STT, TTS, Conversation State

| Module | Status | What it does |
| --- | --- | --- |
| `speech/wakeword.py` | ✅ Built | "Hey Markus" activation via openWakeWord; now uses the cooldown from `conversation_state.py` so a loud utterance can't double-activate |
| `speech/vad.py` | ✅ Built | Standalone voice activity detection (RMS-energy based) — silence timeout ends an utterance, a minimum-speech floor discards noise/clicks, a hard cap prevents a stuck-open mic from recording forever |
| `speech/conversation_state.py` | ✅ Built | `IDLE → ACTIVATED → LISTENING → TRANSCRIBING → PROCESSING → RESPONDING → SPEAKING → IDLE` state machine (illegal transitions raise `InvalidTransitionError`); wake-word cooldown; continuous-conversation mode (follow-up turns skip the wake word if they arrive soon enough) |
| `speech/whisper.py` | ✅ Built | Local speech-to-text via faster-whisper |
| `speech/tts.py` | ✅ Built | Text-to-speech playback |
| `speech/listener.py` | ✅ Built | Microphone capture; `record_utterance()` now delegates to `speech/vad.py` instead of inline threshold logic |

**Config:** `WAKE_WORD_ENABLED`, `WAKE_WORD_THRESHOLD`,
`WAKE_WORD_COOLDOWN`, `VAD_ENABLED`, `VAD_SILENCE_TIMEOUT`,
`VAD_MIN_SPEECH_DURATION`, `VAD_MAX_RECORDING_DURATION`,
`VAD_SILENCE_THRESHOLD`, `CONTINUOUS_CONVERSATION`,
`CONTINUOUS_CONVERSATION_TIMEOUT`.

**Tests:** `tests/test_vad.py` (7 tests) + `tests/test_conversation_state.py`
(10 tests) — synthetic audio frames and fake listeners, no real
microphone needed.

---

## 3. Vision — Camera, Face, Tracking, Gesture, Emotion, Pose, Object

| Module | Status | What it does |
| --- | --- | --- |
| `vision/camera.py` | ✅ Built | Shared OpenCV camera handle for every other vision module |
| `vision/face.py` | ✅ Built | Face detection + recognition against enrolled faces in `assets/known_faces/` |
| `vision/face_tracking.py` | ✅ Built | `FaceTracker` — full detection every `FACE_TRACKING_REDETECT_EVERY_N_FRAMES` frames (default 10), cheap centroid tracking in between, to cut CPU/GPU cost |
| `vision/gesture.py` | ✅ Built | Hand gesture recognition (open palm, fist, thumbs up, pointing) via MediaPipe |
| `vision/emotion.py` | ✅ Built | Facial expression classification via `fer` |
| `vision/pose.py` | ✅ Built | Body pose estimation via MediaPipe |
| `vision/object.py` | ✅ Built | Object detection via YOLO (ultralytics) |
| Screen intelligence / OCR | ❌ Not built | Planned — structured `{application, window_title, visible_error, language}` context instead of sending screenshots to the model |

**Important:** raw camera frames are never sent to the AI model — only
structured summaries (face count, expression + confidence, object
labels). Expression is always phrased as an estimate
(`"appears happy — 72%"`), never asserted as a fact about the user's
internal state.

**Config:** `CAMERA_INDEX`, `FACE_MATCH_THRESHOLD`,
`FACE_TRACKING_REDETECT_EVERY_N_FRAMES`.

**Tests:** `tests/test_face_tracking.py` — 6 tests, fake recognizer, no
real camera needed.

**Graceful degradation:** every optional CV library (`mediapipe`,
`face-recognition`, `ultralytics`, `fer`) degrades to a warning instead
of a crash if missing. `mediapipe` should be pinned to `0.10.14` —
newer builds dropped the legacy `solutions.hands`/`solutions.pose` API
these modules use.

---

## 4. Multimodal Perception Fusion

| Module | Status | What it does |
| --- | --- | --- |
| `brain/perception.py` | ✅ Built | `PerceptionManager`/`PerceptionContext` — fuses audio (`wake_word_detected`, `speaking`, `transcript`) and vision (`face_present`, `face_count`, `expression`, `expression_confidence`) into one object; `to_prompt_context()` renders a hedged, LLM-ready summary |

**Privacy is enforced, not just displayed** — disabling a capability
means updates to it are silently dropped, not just hidden from a UI:

| Flag | Default | Effect when off |
| --- | --- | --- |
| `MICROPHONE_ENABLED` | `true` | `update_audio()` calls are ignored |
| `CAMERA_ENABLED` | `false` | `update_vision()` calls are ignored |
| `EMOTION_DETECTION_ENABLED` | `false` | Expression fields stay empty even if a face is present — presence isn't consent for expression analysis |
| `LOCAL_PROCESSING_ONLY` | `true` | Keeps speech/vision inference on this machine |
| `RAW_AUDIO_RETENTION` / `RAW_VIDEO_RETENTION` / `EMOTION_HISTORY` | `false` | Nothing sensitive persists unless explicitly turned on |

Vision (camera + emotion) defaults **off**; microphone + wake word
default **on**.

**Tests:** `tests/test_perception.py` — 10 tests, including an explicit
assertion that the string `"user is angry"` never appears in generated
prompt context, only the hedged `"appears angry ... not a confirmed
emotional state"` phrasing.

---

## 5. Reasoning & Routing

| Module | Status | What it does |
| --- | --- | --- |
| `brain/router.py` | ⚠️ Partial | Intent classification (`chat`/`code`/`image`/`vision`/`automation`/`system`) + dispatch; still needs to become the full Model Router (task_type/privacy/latency/complexity → OmniRoute route) — `ai/omniroute_client.py`'s `route` parameter is the first piece |
| `brain/memory.py` | ⚠️ Minimal | SQLite conversation history + a flat facts table; works, but should grow into the layered short-term/episodic/preference/project model with a vector store (ChromaDB) — see `ARCHITECTURE.md` §6b |
| `brain/prompts.py` | ✅ Built | System prompt templates |
| Context Manager | ⚠️ Partial | `brain/perception.py` covers the audio/vision half; still needs app-state/screen context merged in |
| Permission Manager | ❌ Not built | Planned — see `ARCHITECTURE.md` §11a for the risk-model design |

---

## 6. Automation & Tools

| Module | Status | What it does |
| --- | --- | --- |
| `brain/commands.py` | ✅ Built | Deterministic regex-based command parser — matches "open X", "close X", "take a screenshot", "set volume to N", "lock the screen", `type "..."`, "search for..." and calls straight into `automation/`. The LLM never decides *whether* to run an action, only how to phrase a reply when nothing matched |
| `automation/apps.py` | ✅ Built | Open/close applications, list running processes |
| `automation/browser.py` | ✅ Built | Selenium-based browser control, page text extraction |
| `automation/keyboard.py` | ✅ Built | Keyboard/mouse control via PyAutoGUI (degrades gracefully with no display) |
| `automation/system.py` | ✅ Built | Screenshots, volume, lock/shutdown/restart (destructive actions require explicit `confirm=True`) |

**Tests:** `tests/test_commands.py` — 9 tests covering every command
pattern plus error handling, with the underlying `automation/` calls
monkeypatched out.

---

## Test suite summary

66 tests total across `tests/`, all offline/mocked — no real gateway,
microphone, camera, or `omniroute` CLI required to run the suite:

| File | Count | Covers |
| --- | --- | --- |
| `test_commands.py` | 9 | Automation command parsing |
| `test_memory.py` | 5 | SQLite conversation/fact storage |
| `test_router.py` | 6 | Full intent→dispatch→remember pipeline |
| `test_omniroute.py` | 13 | Health checker, manager, status API |
| `test_vad.py` | 7 | Voice activity detection |
| `test_conversation_state.py` | 10 | Wake-word state machine, cooldown, continuous conversation |
| `test_face_tracking.py` | 6 | Detection/tracking hybrid |
| `test_perception.py` | 10 | Multimodal fusion, privacy gating |

```bash
pip install pytest --break-system-packages
pytest tests/ -v
```

