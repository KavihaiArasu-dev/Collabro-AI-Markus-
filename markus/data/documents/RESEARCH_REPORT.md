# MARKUS.AI — Deep Research & Technical Architecture Report

*JARVIS-style Voice-Controlled Computer Assistant*  
*Windows • Browser • Applications • Web • Files • Vision • Memory • Security*

---

## 1. Executive Summary

Markus.AI should be designed as a computer-use agent platform rather
than as a simple voice-controlled Python script. The recommended
architecture combines an LLM agent runtime with deterministic Windows
automation, browser automation, controlled filesystem operations, MCP
integrations, voice, computer vision, PostgreSQL memory, and a
permission engine.

The central principle is: use native APIs and deterministic automation
whenever possible, and use visual computer-use automation as a fallback
when an application or website cannot be controlled reliably through a
structured interface.

---

## 2. Core Architecture

```text
USER
  ↓
VOICE / TEXT INPUT
  ↓
MARKUS AGENT
(OpenAI Agents SDK / Responses API)
  ↓
PLANNER + TOOL ROUTER
  ├── Windows tools
  ├── Browser tools
  ├── Filesystem tools
  ├── Web/API tools
  ├── MCP tools
  ├── Vision / Computer Use
  └── Memory
  ↓
PERMISSION ENGINE
  ├── Safe → Execute
  ├── External/Risky → Confirm
  └── Dangerous → Block/Confirm
  ↓
ACTION EXECUTION
  ↓
OBSERVE RESULT
  ↓
RE-PLAN IF REQUIRED
  ↓
VOICE / TEXT RESPONSE
```

---

## 3. Recommended Technology Stack

| Layer | Recommended Technology | Purpose | Priority |
| --- | --- | --- | --- |
| AI / Agent | OpenAI Agents SDK + Responses API | Reasoning, planning, tool orchestration | Core |
| Tool protocol | MCP + function tools | Connect external/local tools and services | Core |
| Voice | OpenAI Realtime / STT + TTS | Natural voice interaction | Core |
| Windows UI | pywinauto + Windows UI Automation | Semantic desktop application control | Core |
| Windows APIs | pywin32 | Deep Windows/COM integration | Core |
| Computer input | PyAutoGUI | Mouse, keyboard, screenshots | Core |
| Processes | psutil | Process/system monitoring | Core |
| Application launch | subprocess | Start approved applications | Core |
| Browser | Playwright | Deterministic web automation | Core |
| Autonomous browser | Browser Use | AI-driven multi-step browser tasks | Optional |
| Vision | OpenCV + vision model | Screen/camera understanding | Later |
| Face recognition | InsightFace + embeddings | Identity recognition | Later |
| Memory | PostgreSQL + pgvector | Persistent semantic memory | Core |
| Security | Permissions + guardrails + approvals | Control side effects | Mandatory |

---

## 4. Agent Runtime — OpenAI Agents SDK

The Agents SDK provides agents configured with instructions, tools,
guardrails, handoffs, sessions and runtime behavior. It can manage agent
turns and tool calls instead of requiring a custom orchestration loop.

- Use the SDK as the main orchestration layer.
- Expose narrowly scoped Python functions as tools.
- Use sessions for conversation continuity.
- Use tracing for debugging and evaluation.
- Use human-in-the-loop approval for sensitive operations.
- Use MCP when an external/local integration should be exposed as a
  standardized tool server.

---

## 5. Windows Control

Windows automation should use a hierarchy. First prefer native/system
APIs, then semantic UI automation, then coordinate-based mouse/keyboard
automation.

```text
Native API / subprocess
  ↓
pywinauto / Windows UI Automation
  ↓
PyAutoGUI fallback
  ↓
Screenshot + vision-based computer use
```

- **pywinauto:** buttons, fields, menus, windows and controls exposed
  through Windows UI Automation.
- **pywin32:** Windows APIs and COM integrations.
- **psutil:** process, CPU, memory, disk and system state.
- **subprocess:** controlled application launching.
- **PyAutoGUI:** mouse, keyboard and screenshot fallback.

---

## 6. Browser Automation

Playwright should be the primary deterministic browser layer. It can
automate Chromium, Firefox and WebKit and is suitable for navigation,
forms, clicks, tabs, screenshots and extraction.

- Use Playwright for predictable workflows.
- Use Browser Use only where autonomous browser reasoning provides a
  real advantage.
- Do not use coordinate-based desktop automation for normal website
  workflows when DOM automation is available.

---

## 7. MCP Integration

Model Context Protocol provides a standardized way to expose tools and
context to an AI model. For Markus.AI, MCP can become the integration
layer for services such as GitHub, Gmail, calendars, databases, files
and other trusted systems.

```text
Markus Agent
  ↓
MCP Client
  ├── GitHub MCP
  ├── Database MCP
  ├── Filesystem MCP
  ├── Productivity MCP
  └── Custom Markus MCP servers
```

Use allow-lists and least-privilege credentials. Sensitive MCP
operations should require approval.

---

## 8. Voice Architecture

```text
Microphone
  ↓
Voice Activity Detection
  ↓
Speech Recognition / Realtime
  ↓
Markus Agent
  ↓
Tool execution
  ↓
Response generation
  ↓
Streaming speech
  ↓
Speaker
```

- For conversational interaction, prefer a realtime voice architecture.
- Support interruption/barge-in so the user can stop Markus
  mid-response.
- Keep voice recognition and tool execution separate so commands can
  also arrive as text.

---

## 9. Computer Vision and GUI Agents

Vision should be a fallback/high-level capability, not the first
mechanism used for every action. A visual computer-use loop can observe
a screenshot, predict an action, execute it, observe the new state and
repeat.

```text
Screenshot → Vision/GUI model → Action → Computer → Screenshot → Repeat
```

- Use visual control when semantic APIs are unavailable.
- Use screen understanding for diagnosing unknown UI states.
- Consider GUI-agent projects such as UI-TARS as research references
  rather than making them the entire foundation.

---

## 10. Memory Architecture

```text
                    MARKUS
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   Short-term memory         Long-term memory
          │                         │
   Agent session          PostgreSQL + pgvector
                                     │
                          semantic embeddings
                                     │
                      preferences / history /
                        projects / context
```

- PostgreSQL stores structured state.
- pgvector stores semantic embeddings.
- Keep sensitive information minimized and permission-controlled.
- Separate short-term conversation state from long-term memory.

---

## 11. Permission and Security Model

A computer-control assistant can cause real-world side effects. Security
must therefore be part of the architecture rather than an afterthought.

| Level | Examples | Policy |
| --- | --- | --- |
| L0 — Read | System status, process list, time, screen | Automatically allowed |
| L1 — Safe | Open app, open website, create folder | Normally automatic |
| L2 — External | Send email/message, upload, publish | Require confirmation |
| L3 — Dangerous | Delete files, arbitrary shell, registry/system changes | Strong confirmation or block |

---

## 12. Tool Design

Prefer small, typed, auditable tools such as:

```text
open_application(app_name)
close_application(app_name)
get_running_processes()
take_screenshot()
click_element(target)
type_text(text)
press_key(key)
open_url(url)
search_web(query)
read_file(path)
create_file(path, content)
create_folder(path)
search_files(query)
check_service(service_name)
run_approved_command(command)
send_message(recipient, message)   # approval required
```

Never expose unrestricted `os.system()`, arbitrary PowerShell, or
unrestricted shell execution directly to the model.

---

## 13. Recommended Project Structure

```text
Markus.AI/
├── core/
│   ├── agent.py
│   ├── planner.py
│   ├── tool_router.py
│   ├── context.py
│   ├── memory.py
│   └── permissions.py
├── voice/
│   ├── realtime.py
│   ├── speech_to_text.py
│   └── text_to_speech.py
├── computer/
│   ├── windows.py
│   ├── keyboard.py
│   ├── mouse.py
│   ├── screenshot.py
│   └── processes.py
├── browser/
│   ├── playwright.py
│   ├── search.py
│   └── autonomous.py
├── apps/
│   ├── launcher.py
│   ├── vscode.py
│   └── integrations/
├── filesystem/
│   ├── files.py
│   └── folders.py
├── vision/
│   ├── screen.py
│   └── face.py
├── mcp/
│   ├── client.py
│   └── servers/
├── database/
│   ├── postgres.py
│   └── vector_memory.py
├── security/
│   ├── policy.py
│   └── approvals.py
└── main.py
```

---

## 14. Installation Plan

Start with the minimum stable foundation:

```bash
python -m venv .venv
.venv\Scripts\activate

pip install openai-agents
pip install pywinauto pywin32 pyautogui psutil
pip install playwright
pip install psycopg[binary] pgvector
pip install opencv-python
pip install python-dotenv pydantic

playwright install
```

Add Browser Use, advanced vision, face recognition and additional MCP
servers only after the core agent/tool architecture is working.

---

## 15. Development Roadmap

- **Phase 1 — Core Agent:** Agent runtime, tool calling, application
  launcher, process awareness and permissions.
- **Phase 2 — Windows Control:** pywinauto, Windows UI Automation,
  PyAutoGUI fallback and screenshots.
- **Phase 3 — Browser:** Playwright, web search and browser workflows.
- **Phase 4 — Voice:** Realtime or streaming speech input/output and
  interruption handling.
- **Phase 5 — Memory:** PostgreSQL, pgvector, session memory and
  user/project context.
- **Phase 6 — MCP:** Trusted external integrations and custom Markus
  MCP servers.
- **Phase 7 — Vision:** Screen understanding, computer-use fallback and
  camera capabilities.
- **Phase 8 — Advanced Agent:** Long-running tasks, proactive
  workflows, specialist agents and evaluation.

---

## 16. Design Principles

- Prefer APIs over GUI automation whenever an API exists.
- Prefer semantic UI automation over screen coordinates.
- Prefer DOM/browser automation over mouse coordinates for websites.
- Use visual computer use as a fallback, not as the universal
  mechanism.
- Expose small, typed, permission-aware tools.
- Require approval for external and destructive actions.
- Keep credentials outside prompts and tool arguments whenever
  possible.
- Log tool calls and outcomes for debugging and security auditing.
- Separate agent reasoning from execution.
- Keep the system modular so individual tools can be replaced without
  rewriting the agent.

---

## 17. Final Recommended Stack

For Markus.AI, the recommended foundation is:

```text
OpenAI Agents SDK
+ MCP + Function Tools
+ pywinauto + Windows UI Automation
+ pywin32 + psutil + subprocess
+ PyAutoGUI
+ Playwright
+ OpenAI Realtime / voice pipeline
+ OpenCV + vision model
+ PostgreSQL + pgvector
+ Permission / approval engine
```

---

## 18. Research References

- **OpenAI Agents SDK — Agents:** <https://openai.github.io/openai-agents-python/agents/>
- **OpenAI Agents SDK — MCP:** <https://openai.github.io/openai-agents-python/mcp/>
- **OpenAI Agents SDK — Tools:** <https://openai.github.io/openai-agents-python/ref/tool/>
- **OpenAI Agents SDK — Guardrails:** <https://openai.github.io/openai-agents-python/guardrails/>
- **OpenAI Agents SDK — GitHub:** <https://github.com/openai/openai-agents-python>
- **Playwright Python:** <https://playwright.dev/python/>
- **pywinauto:** <https://github.com/pywinauto/pywinauto>
- **PyAutoGUI:** <https://github.com/asweigart/pyautogui>
- **pywin32:** <https://github.com/mhammond/pywin32>
- **Browser Use:** <https://github.com/browser-use/browser-use>
- **UI-TARS:** <https://github.com/bytedance/UI-TARS>

---

## 19. Conclusion

Markus.AI should be implemented as a permission-aware computer-use
agent. The LLM should decide what needs to happen, while specialized
tools perform the actual work. Deterministic APIs should be preferred
for reliability; Windows UI Automation and Playwright should handle
structured interfaces; visual computer use should handle ambiguous or
inaccessible interfaces; MCP should provide a standardized integration
layer; and PostgreSQL/pgvector should provide persistent memory.

This architecture is scalable from a personal desktop assistant into a
broader autonomous agent platform without requiring a rewrite of the
core system.

---

## Note: relationship to the rest of the Markus.AI documentation set

This report recommends a **different stack** than `ARCHITECTURE.md` /
`SKILLS.md` in some places — most notably **OpenAI Agents SDK** instead
of the OmniRoute-gateway approach, and **pywinauto/pywin32/Playwright**
(Windows-native, agent-driven automation) instead of the
`brain/commands.py` deterministic-regex + `automation/` approach already
built and tested in the Markus-AI codebase. Both share the same core
principles (prefer deterministic APIs over vision, permission-gate
risky actions, keep reasoning separate from execution) — the difference
is mainly in *which* agent runtime and automation libraries carry those
principles out. Treat this file as an alternative/competing proposal to
reconcile with the existing docs, not as something already implemented.
