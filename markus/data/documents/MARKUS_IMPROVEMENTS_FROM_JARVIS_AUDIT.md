# Markus AI — Improvements from the JARVIS Repository Audit

This reviews `JARVIS_Deep_Repository_Audit_Report.docx` (audit of
`github.com/deestudio028-droid/jarvis`, commit `6de90d9`) against
Markus's actual codebase, cross-checked directly against the real
repository's README/structure (fetched live — see §6). It's organized
in two halves: **features worth adopting**, and **mistakes to avoid** —
the second half found a real, live bug in Markus's own code, not just a
hypothetical.

---

## 0. Top finding — a real bug, not a hypothetical

The audit's #1 security finding in JARVIS is `shell=True` in
`open_app.py`, letting an LLM-influenced string reach a shell
interpreter. **Markus's own `automation/apps.py` has the identical
pattern:**

```python
# automation/apps.py — current code
if SYSTEM == "Windows":
    subprocess.Popen(["start", "", name], shell=True)
```

`name` here comes straight from `brain/commands.py`'s regex extraction
of free-text user input (`open (.+)`), which is exactly the "user voice
→ model intent → generated application string → shell interpreter"
chain the audit calls the undesirable path. This should be treated as
**P0**, same as the audit's own top item. Fix:

```python
# Corrected: no shell=True, and the app name goes through a registry,
# not straight into a command interpreter.
if SYSTEM == "Windows":
    subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
```

That's the minimal fix. The complete fix (matching §7 below) resolves
`name` through an application registry/allowlist *before* it ever
reaches `subprocess`, so an unrecognized or malformed string is
rejected rather than passed through at all.

---

## 1. Executive comparison

| | JARVIS (audited) | Markus (current) |
|---|---|---|
| Feature breadth | 9/10 — very broad (WhatsApp bridge, drone control, dashboard, dynamic plugins) | Narrower by design — voice, vision, automation, multi-agent chat |
| AI-agent architecture | 8/10 — Gemini Live native-audio + Ollama fallback | OmniRoute gateway + 8-agent roster (`agents/`) |
| Security architecture | 5/10 — shell=True, unauthenticated-by-default LAN dashboard, CBC without auth | Partially ahead: `agents/orchestrator.py` already gates HIGH-risk actions behind confirmation — but shares JARVIS's exact `shell=True` bug (§0) |
| Production readiness | 5.5/10 | Comparable — both are pre-production prototypes |
| Test discipline | 50 unit tests, explicitly covering audio-loopback recovery and LLM 404 resilience | 77 tests, strong on module boundaries; weaker on "gateway fails mid-request" resilience (§5) |

The overall lesson: JARVIS's feature breadth is genuinely impressive and
several of its ideas are worth adopting (§2-3), but its core finding —
*"the main limitation is not capability, it is control-plane
security"* — is a warning Markus should heed **before** growing its
feature surface the way JARVIS did, not after.

---

## 2. Features worth adopting

**Hybrid cloud/local intelligence with graceful fallback.** JARVIS
defaults to Gemini Live native-audio streaming
(`gemini-2.5-flash-native-audio-preview-12-2025`, 16kHz mono in /
24kHz mono out) and falls back to fully offline Ollama models
(llama3.2, llama3.1, qwen, gemma) with no cloud dependency. Markus's
OmniRoute gateway already generalizes this (§6a in `ARCHITECTURE.md`),
but doesn't yet have a dedicated "live native audio" route — recommend
adding `"live"` to `config.OMNIROUTE_ROUTES` for genuinely
low-latency voice-to-voice models, distinct from the existing
`speech_and_music` capability which currently maps to text-in/audio-out
TTS rather than native audio-to-audio.

**GPU-aware STT with automatic fallback.** JARVIS runs CUDA-accelerated
faster-whisper on NVIDIA GPUs with automatic graceful CPU fallback
(int8). Markus's `speech/whisper.py` currently hard-codes
`device="cpu", compute_type="int8"` — worth detecting CUDA availability
at startup and switching device/compute_type automatically, falling
back to the current CPU/int8 path exactly as-is when no GPU is present.

**Zero-code plugin engine with crash isolation.** JARVIS's
`core/plugin_loader.py` drops any `.py` file into `plugins/` and
auto-registers it, validating metadata/callable interfaces, skipping
malformed modules, and never letting one bad plugin abort the whole
scan. Markus doesn't have an equivalent — `agents/` and `automation/`
are fixed, hand-written modules. If Markus grows a plugin surface, this
crash-isolation pattern (try/except per-module import, continue past
failures, log and skip rather than abort) is the right shape to copy —
but see §3's caveat: JARVIS's own audit notes this is crash isolation,
not security sandboxing, and recommends worker-process isolation for
risky plugins. Markus should design that in from the start rather than
retrofitting it later.

**Native desktop HUD as a third option.** JARVIS's `ui.py` is a PyQt6
HUD with waveforms, telemetry, and camera feed — a working example of
the native-desktop-app path that `ARCHITECTURE.md` currently only
sketches (PySide6, not yet built) alongside the browser-based HUD
explored in other docs. Worth treating PyQt6/PySide6 code from a real,
working reference like this as a starting point if the native path is
chosen over the browser path.

**Resilience-focused test naming.** JARVIS's test suite explicitly
targets failure modes — "audio loopback recovery," "VAD adaptation,"
"LLM 404 resilience" — not just happy-path coverage. See §5 for the
concrete gap this reveals in Markus's own suite.

---

## 3. Mistakes to avoid (with where Markus already does better, and where it doesn't)

**`shell=True` with LLM-influenced strings.** Covered in §0 — Markus
has this bug too. Fix: resolve app names through a registry/allowlist,
never pass a free-text string into a shell interpreter.

**Dashboard bound to `0.0.0.0` by default with automatic firewall
setup.** Markus doesn't have a dashboard yet, but when `server.py`
grows into one (per `ARCHITECTURE.md`'s HUD plans), it must default to
`127.0.0.1` and require explicit opt-in for LAN exposure — precisely
the fix the audit recommends for JARVIS. Write this down now, before
the dashboard exists, so it's not a retrofit.

**Encryption without authentication (AES-CBC).** Same — not yet
relevant (no encrypted remote channel exists in Markus yet), but
pre-commit to AES-256-GCM or ChaCha20-Poly1305 for any future
session/device encryption rather than defaulting to CBC.

**Persistent bearer tokens in `localStorage` / URL query strings.**
Same category — a preventative note for whenever Markus builds
device-pairing or download-authorization flows.

**Scattered secrets access.** JARVIS has multiple modules independently
reading `config/api_keys.json`. **Markus already does this correctly**
— `config.py` is the single place environment variables are read
(`OMNIROUTE_API_KEY`, `GOOGLE_API_KEY`, etc.) — worth explicitly
preserving as new modules get added, not something to fix.

**No policy/risk engine between LLM proposals and execution.** This is
JARVIS's single biggest finding, and **Markus is already ahead here**:
`agents/orchestrator.py`'s `Orchestrator.handle()` blocks HIGH-risk
automation (delete/shutdown/restart/format/uninstall) behind an
explicit confirmation callback before `brain/commands.py` ever executes
— this is exactly the "Policy/risk engine" step the audit recommends
JARVIS add. The gap: JARVIS's audit proposes a **6-level** risk scale
(R0 read-only → R5 physical action); Markus currently only distinguishes
two (auto-execute vs. blocked-until-confirmed). See §4 for a proposed
upgrade.

**No structured audit log.** Neither JARVIS nor Markus has this yet —
already tracked as an open item in `ARCHITECTURE.md` §11a and
`SKILLS.md` §7. Reinforcing it here since the audit independently
arrives at the same gap.

**Unpinned/unscanned dependencies.** JARVIS's audit recommends pinning
versions, a lock file, vulnerability scanning, and an SBOM. **Markus's
`requirements.txt` already pins exact versions** (`fastapi==0.115.0`,
etc.) — ahead of where JARVIS's audit found it. Still missing: a lock
file, automated vulnerability scanning, and SBOM generation for
releases — worth adding as the dependency list grows.

---

## 4. Proposed risk-tier upgrade for `agents/orchestrator.py`

Adopt the audit's R0-R5 scale in place of Markus's current binary
LOW/HIGH split:

| Class | Examples | Default policy | Markus mapping today |
|---|---|---|---|
| R0 — Read-only | Weather, web search, system status, file listing | No confirmation | Currently: auto (LOW) |
| R1 — Reversible | Open apps, volume, browser navigation, media | Normally no confirmation | Currently: auto (LOW) |
| R2 — Persistent | Write/delete files, install packages, modify settings | Confirmation for sensitive actions | **Currently missing** — Markus's `_HIGH_RISK_PATTERN` treats delete the same as R4/R5 |
| R3 — External communication | Send email/message, uploads, posts | Explicit confirmation | Not applicable yet — Markus has no messaging/upload tools |
| R4 — System-critical | Shutdown, restart, firewall/security changes | Explicit confirmation | Currently: HIGH (blocked) |
| R5 — Physical action | Drone/external device control | Confirmation + safety constraints | Not applicable — Markus has no physical actuators |

The concrete gap this surfaces: Markus's `_HIGH_RISK_PATTERN` in
`agents/orchestrator.py` currently matches `delete|remove|shutdown|
restart|format|rm -rf|uninstall` as one undifferentiated HIGH tier.
Splitting `delete a file` (R2 — persistent, damage is contained and
sometimes recoverable) from `shutdown|restart|format` (R4 —
system-critical, no undo) would let file deletion get a lighter
confirmation prompt than a system shutdown, instead of treating them
identically.

---

## 5. Test suite gap this audit surfaces

JARVIS's suite explicitly tests "LLM 404 resilience" — what happens
when the model backend returns an error mid-request. Markus's
`tests/test_omniroute.py` tests offline/auth/provider-error *health
checks* thoroughly, but there isn't yet a test for **a request that
starts successfully and then the gateway errors mid-stream** (e.g.
`generate_text()` raising partway through, or a `stream_text()`
generator failing after yielding some chunks). Recommend adding this
alongside the existing suite — it's a realistic failure mode
(`ai/omniroute_client.py`'s `stream_text()` has no error handling
around the `for chunk in stream` loop today).

---

## 6. Verification note

This document's claims about Markus's own code are grounded directly
in the files in the Markus-AI project (`automation/apps.py`,
`agents/orchestrator.py`, `speech/whisper.py`, `config.py`,
`requirements.txt`) as of this conversation. Claims about JARVIS are
grounded in the audit report plus a live fetch of
`github.com/deestudio028-droid/jarvis`'s README, which independently
confirms the repository structure the audit describes (`core/
llm_client.py`, `core/plugin_loader.py`, `plugins/whatsapp_voice_
bridge.py`, `dashboard/`, `config/api_keys.json.example`, a 50-test
suite under `tests/`) — the audit's specific file-level claims weren't
independently re-verified line-by-line (GitHub blocks automated
directory/file browsing beyond the repo root), but the structural
match is a good corroborating signal that the audit is describing the
real repository accurately.

---

## 7. Priority action list for Markus

**P0 — Immediate**
- Fix `automation/apps.py`'s `shell=True` (§0) — same bug class as
  JARVIS's top finding.
- Resolve application names through a registry/allowlist before they
  reach `subprocess`, rather than passing `brain/commands.py`'s
  regex-extracted string straight through.

**P1 — Security hardening**
- Split the risk tiers per §4 (R0-R5 instead of LOW/HIGH).
- Write down the "localhost by default, LAN is opt-in" rule for any
  future dashboard now, before one exists.
- Pre-commit to AES-GCM/ChaCha20-Poly1305 for any future
  encrypted-channel work.

**P2 — Architecture**
- Add the structured audit log already tracked in `ARCHITECTURE.md`
  §11a.
- If a plugin system is added, design worker-process isolation in from
  the start rather than crash-isolation-only.
- Add the "gateway fails mid-stream" test from §5.

**P3 — Reliability**
- Add a dependency lock file and automated vulnerability scanning on
  top of the version pinning already in place.
- Detect CUDA availability in `speech/whisper.py` and switch
  device/compute_type automatically, falling back to the current
  CPU/int8 path when no GPU is present.
