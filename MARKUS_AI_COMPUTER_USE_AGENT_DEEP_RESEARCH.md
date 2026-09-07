# Markus AI — Computer-Use Agent Deep Research

*Architecture, Packages, Training Strategy & Implementation Roadmap*

**Objective.** Build a Windows-based voice AI assistant that can
understand natural-language commands, open applications and websites,
control music, automate browsers and desktop applications, observe
results, verify actions, remember preferences, and safely execute
multi-step tasks.

---

## 1. Executive Recommendation

Do not begin by training an AI model from scratch. Markus should
initially be built as an AI agent around an existing language model. The
model performs intent understanding, planning, tool selection and
reasoning; deterministic local tools perform the actual computer
actions.

```text
User → Speech-to-Text → LLM → Tool Router → Permission Check
     → Windows / Browser / Music / Web Tools → Observation → Verification
     → Memory → Text-to-Speech → User
```

Training or fine-tuning becomes useful later, after Markus has
accumulated representative successful and failed interaction traces.

---

## 2. Core Architecture

```text
MARKUS
  │
  Voice / Text Input
  │
  ▼
  Speech-to-Text
  │
  ▼
  LLM (Intent + Planning + Tools)
  │
  ▼
  Tool Router
  │
  Permission / Validation
  │
  ┌────────────────────┼────────────────────┐
  ▼                    ▼                    ▼
  Windows Automation   Browser Automation   Service APIs
  │                    │                    │
  UI Automation        Playwright           Music / Web
  pywinauto            DOM / selectors      integrations
  PowerShell (safe)
  subprocess
  PyAutoGUI fallback
  │                    │                    │
  └────────────────────┼────────────────────┘
                       ▼
                  Observation
                       │
                     Verify
                    /       \
              Failed        Success
                  │             │
              Replan         Memory
                  │
                  ▼
             Text-to-Speech
```

---

## 3. What Markus Should Be Able To Do

- Open and close Windows applications such as Chrome, VS Code, Notepad
  and Calculator.
- Open configured websites such as YouTube, GitHub, LinkedIn and Figma.
- Search the web and automate supported websites.
- Search for and control music using supported APIs or browser
  automation.
- Type text, click controls, scroll, use hotkeys and capture
  screenshots.
- Inspect Windows application UI elements and invoke controls
  programmatically.
- Perform multi-step tasks using a plan → action → observation →
  verification loop.
- Remember approved user preferences, application aliases, projects
  and workflows.
- Ask for confirmation before risky operations such as deleting files
  or executing sensitive commands.

---

## 4. Recommended Technology Stack

| Layer | Recommended Technology | Purpose |
|---|---|---|
| LLM / reasoning | OpenAI SDK or equivalent | Intent, planning, tool calling |
| Structured tools | Function/tool calling + Pydantic | Validated actions and arguments |
| Backend | Python + FastAPI + Uvicorn | Agent server and APIs |
| Speech-to-text | Faster-Whisper or hosted STT | Voice command recognition |
| Text-to-speech | Neural TTS or local TTS | Voice responses |
| Browser | Playwright | DOM/browser automation |
| Windows UI | Microsoft UI Automation + pywinauto | Semantic desktop automation |
| Fallback input | PyAutoGUI | Mouse, keyboard, screenshots |
| System | Controlled PowerShell/subprocess | Approved OS operations |
| Memory | SQLite first; vector store later | Preferences and task history |
| Frontend | React + TypeScript + Tailwind | Assistant dashboard |
| Realtime | WebSockets | Live agent state and events |

---

## 5. Python Packages

```bash
pip install openai
pip install fastapi uvicorn pydantic python-dotenv
pip install faster-whisper sounddevice numpy
pip install playwright
pip install pywinauto pyautogui
pip install requests
pip install chromadb

playwright install
```

Install only what the current implementation needs. ChromaDB/vector
memory, for example, can be postponed until basic task execution is
stable.

---

## 6. Tool-Calling Design

Expose narrow, typed tools instead of allowing the LLM to generate
arbitrary Python or PowerShell.

```text
open_application(application)
open_website(url_or_alias)
search_web(query)
search_youtube(query)
play_music(query)
pause_music()
resume_music()
next_track()
close_application(application)
take_screenshot()
find_ui_element(name, control_type)
click_ui_element(target)
type_text(text)
scroll(direction, amount)
open_file(path)
open_folder(path)
get_system_info()
run_approved_command(command_id)
```

The LLM should select a tool and provide structured arguments. The
backend validates those arguments, checks permissions, executes the
action and returns a structured result.

---

## 7. Windows Automation Strategy

Use Windows UI Automation as the primary semantic desktop-control layer.
Microsoft describes UI Automation as a Windows accessibility framework
that provides programmatic access to most desktop UI elements and
enables applications to retrieve and manipulate those elements. UI
elements form a tree with the desktop as the root; controls expose
properties and control patterns.

Preferred hierarchy:

1. Application API / command interface
2. Windows UI Automation
3. Application accessibility tree
4. Browser DOM / Playwright
5. Vision-based grounding
6. PyAutoGUI coordinate fallback

UI Automation is preferable to raw screen coordinates because controls
can be identified by semantic properties such as name and control type,
and can expose control patterns such as Invoke or Scroll.

---

## 8. Browser Automation with Playwright

Use Playwright for websites and web applications. It supports Chromium,
Firefox and WebKit and provides synchronous and asynchronous Python
APIs.

```bash
pip install playwright
playwright install
```

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://example.com")
    print(await page.title())
    await browser.close()
```

For robust browser automation, prefer semantic locators and page state
over fixed screen coordinates.

---

## 9. Voice Pipeline

```text
Microphone
  ↓
Wake-word detector
  ↓
Speech-to-Text
  ↓
LLM
  ↓
Tool execution
  ↓
Response text
  ↓
Text-to-Speech
  ↓
Speaker
```

Faster-Whisper is a practical local STT candidate. A dedicated wake-word
layer prevents every microphone utterance from being sent to the agent.

---

## 10. Music Control

Use an official service API when it provides the required
playback/search capability. Otherwise, use browser automation for
supported web players or OS-level media controls where appropriate.

```text
"Play relaxing music"
  ↓
play_music(query="relaxing music")
  ↓
Music API / browser
  ↓
Verify playback state
```

---

## 11. Agent Loop

```python
while task_not_complete:
    goal = understand_goal()
    action = plan_next_action(goal)
    validate(action)
    result = execute(action)
    observation = observe(result)
    verified = verify(observation)

    if not verified:
        recover_or_replan()

respond_to_user()
```

Verification is essential. After an action such as opening an
application or clicking Play, Markus should check process/window state,
UI state, DOM state, or another reliable observation.

---

## 12. Application Discovery and Aliases

Maintain an application registry so Markus can resolve natural language
to installed applications.

```json
{
  "vscode": {
    "name": "Visual Studio Code",
    "aliases": ["vs code", "vscode", "visual studio code"],
    "executable": "..."
  }
}
```

A similar website registry can map aliases such as 'my GitHub' or
'YouTube' to approved URLs.

---

## 13. Memory Architecture

```text
Short-term memory        → current conversation and active task
Long-term structured     → preferences, app aliases, projects, approved workflows
Vector memory (optional) → semantic retrieval of prior notes / task context
Execution history        → tool calls, results, failures and recovery traces
```

---

## 14. Security and Permission Model

Treat computer access as a privileged capability. Never connect the LLM
directly to unrestricted shell execution.

| Risk | Examples | Policy |
|---|---|---|
| Low | Open app, open website, search, play/pause music | Usually automatic |
| Medium | Move/delete a file, upload, send message | Require confirmation or policy |
| High | Arbitrary shell, registry/security changes, bulk deletion | Explicit confirmation; ideally sandboxed |

During development, test autonomous operations in a controlled Windows
environment or VM. Keep credentials and secrets out of model prompts and
tool outputs.

---

## 15. Training Strategy

Do not fine-tune the main model first. Build deterministic tools and
collect execution traces.

```json
{
  "command": "open my browser",
  "intent": "OPEN_APPLICATION",
  "tool": "open_application",
  "arguments": {"application": "chrome"},
  "result": "success"
}
```

After collecting a substantial dataset, training or fine-tuning can
target intent classification, tool selection, argument extraction,
action planning or UI grounding. Evaluation should include both
successful and failed tasks.

---

## 16. Development Roadmap

1. **V1** — Text agent: user → LLM → response.
2. **V2** — Tool calling: open apps, open websites, search.
3. **V3** — Voice: wake word, STT and TTS.
4. **V4** — Application registry and aliases.
5. **V5** — Browser agent with Playwright.
6. **V6** — Windows UI Automation and pywinauto.
7. **V7** — Observation and verification.
8. **V8** — Memory and user preferences.
9. **V9** — Vision-based computer use.
10. **V10** — Multi-step autonomous planning and recovery.
11. **V11** — Evaluation dataset, fine-tuning experiments and safety testing.

---

## 17. Recommended Markus Folder Structure

```text
MARKUS/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── agent/
│   │   ├── agent.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── observer.py
│   │   ├── verifier.py
│   │   └── recovery.py
│   ├── llm/
│   │   ├── client.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   ├── voice/
│   │   ├── microphone.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   └── wakeword.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── applications.py
│   │   ├── websites.py
│   │   ├── browser.py
│   │   ├── music.py
│   │   ├── windows.py
│   │   ├── filesystem.py
│   │   └── screenshot.py
│   ├── automation/
│   │   ├── playwright.py
│   │   ├── windows_uia.py
│   │   ├── pywinauto.py
│   │   └── pyautogui.py
│   ├── memory/
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   └── vector.py
│   └── security/
│       ├── permissions.py
│       ├── validator.py
│       ├── risk.py
│       └── confirmation.py
├── frontend/
├── tests/
├── data/
├── .env
├── requirements.txt
└── README.md
```

---

## 18. First Working MVP

The first end-to-end milestone should support these commands:

- "Open Chrome."
- "Open VS Code."
- "Open YouTube."
- "Search YouTube for relaxing music."
- "Play music."
- "Open GitHub."
- "Take a screenshot."

Once these work reliably, add browser interaction, desktop UI
automation, observation/verification, memory and multi-step planning.

---

## 19. Research References

- **Microsoft Learn — UI Automation Overview:** Microsoft UI Automation
  provides programmatic access to most Windows desktop UI elements and
  supports manipulation of UI through automation clients.
- **Microsoft Learn — UI Automation Tree Overview:** Windows UI
  Automation exposes a desktop-rooted tree of application windows and
  UI controls.
- **Microsoft Learn — UI Automation Control Patterns:** Control patterns
  such as Invoke and Scroll expose specific control functionality.
- **Playwright Python Documentation:** Playwright provides browser
  automation for Chromium, Firefox and WebKit with sync and async
  Python APIs.

---

## 20. Final Technical Recommendation

Build Markus as a controlled computer-use agent rather than as a
monolithic trained model. The strongest initial Windows stack is
Python + an LLM with structured tool calling + FastAPI +
Faster-Whisper + neural TTS + Playwright + Windows UI
Automation/pywinauto + PyAutoGUI fallback + SQLite memory +
React/Tailwind dashboard. Add vision and fine-tuning only after the
deterministic agent loop is stable and measurable.

---

## Note: relationship to the rest of the Markus.AI documentation set

This is the third "computer-use agent" proposal in this documentation
set, and it overlaps heavily with `MARKUS_AI_DEEP_RESEARCH_TECHNICAL_REPORT.md`
(same OpenAI SDK + pywinauto + Playwright direction) rather than the
OmniRoute-gateway + `brain/commands.py`/`automation/` approach actually
built and tested in the Markus-AI codebase (`ARCHITECTURE.md`/`SKILLS.md`).
The permission/risk model here (Low/Medium/High) is the same shape as
the one already implemented in `agents/orchestrator.py` — that's a point
of genuine agreement across all the proposals worth keeping, regardless
of which automation stack you settle on. The folder structure and tool
list here are a reasonable reference if you ever do rebuild the
automation layer on Windows UI Automation/pywinauto instead of the
current `automation/` package.
