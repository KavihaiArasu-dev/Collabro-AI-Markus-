"""
Markus AI — System Constants

All enums, state definitions, risk levels, and routing constants used throughout the system.
"""

from __future__ import annotations

from enum import Enum


# ── AI States (§6 of the design spec) ──

class AIState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    PLANNING = "planning"
    CODING = "coding"
    RESEARCH = "research"
    EXECUTING = "executing"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    SPEAKING = "speaking"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# ── OmniRoute Routing Aliases (§6a) ──

class RouteAlias(str, Enum):
    AUTO = "auto/chat"
    FAST = "auto/fast"
    CODING = "auto/coding"
    CHEAP = "auto/cheap"
    OFFLINE = "auto/offline"
    SMART = "auto/smart"


# ── Provider Tiers (§6a) ──

class ProviderTier(str, Enum):
    TIER_A = "general_intelligence"   # Gemini, Claude, OpenAI, DeepSeek, Mistral, Qwen
    TIER_B = "fast_intelligence"      # Groq, Cerebras
    TIER_C = "local_intelligence"     # Ollama, LM Studio, vLLM


# ── Intent Types (§4 — Intent Classifier) ──

class IntentType(str, Enum):
    CHAT = "chat"
    QUESTION = "question"
    SEARCH = "search"
    CODE = "code"
    DEBUG = "debug"
    FILE_OPERATION = "file_operation"
    APP_CONTROL = "app_control"
    SYSTEM_CONTROL = "system_control"
    BROWSER_AUTOMATION = "browser_automation"
    RESEARCH = "research"
    AUTOMATION = "automation"
    REVIEW = "review"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    TASK_MANAGEMENT = "task_management"
    MULTI_STEP_ACTION = "multi_step_action"
    MEMORY = "memory"
    RAG = "rag"
    SETTINGS = "settings"
    VOICE_COMMAND = "voice_command"
    YOUTUBE = "youtube"


# ── Tool Risk Levels (§11a) ──

class RiskLevel(str, Enum):
    LOW = "low"         # read file, search web, open application
    MEDIUM = "medium"   # write file, run dev command, change app settings
    HIGH = "high"       # delete file, destructive shell, send email, upload private data


# ── Permission Decisions (§11a) ──

class PermissionDecision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    BLOCK = "block"


# ── Memory Categories (§6b) ──

class MemoryCategory(str, Enum):
    TEMPORARY = "temporary"
    SESSION = "session"
    PREFERENCE = "preference"
    PROJECT = "project"
    IMPORTANT = "important"


# ── Memory Types (§6b) ──

class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    EPISODIC = "episodic"
    PREFERENCE = "preference"
    PROJECT = "project"


# ── Agent Types (§5) ──

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    RESEARCHER = "researcher"
    DOCUMENTATION = "documentation"
    UI_UX = "ui_ux"
    AUTOMATION = "automation"
    MEMORY = "memory"


# ── Agent Status ──

class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


# ── Agent default routing (§5 per-agent defaults) ──

AGENT_DEFAULT_ROUTES: dict[AgentType, RouteAlias] = {
    AgentType.ORCHESTRATOR: RouteAlias.AUTO,
    AgentType.ARCHITECT: RouteAlias.SMART,
    AgentType.CODER: RouteAlias.CODING,
    AgentType.REVIEWER: RouteAlias.CODING,
    AgentType.DEBUGGER: RouteAlias.SMART,
    AgentType.RESEARCHER: RouteAlias.AUTO,
    AgentType.DOCUMENTATION: RouteAlias.AUTO,
    AgentType.UI_UX: RouteAlias.AUTO,
    AgentType.AUTOMATION: RouteAlias.FAST,
    AgentType.MEMORY: RouteAlias.FAST,
}


# ── Model Profiles (§6a) ──

MODEL_PROFILES: dict[str, dict] = {
    "normal":  {"route": RouteAlias.AUTO,    "description": "Normal conversation"},
    "fast":    {"route": RouteAlias.FAST,     "description": "Fast answer"},
    "coding":  {"route": RouteAlias.CODING,   "description": "Programming"},
    "cheap":   {"route": RouteAlias.CHEAP,    "description": "Cost saving"},
    "offline": {"route": RouteAlias.OFFLINE,  "description": "Local/private"},
    "smart":   {"route": RouteAlias.SMART,    "description": "Adaptive reasoning"},
}


# ── Permission Defaults (§11a) ──

PERMISSION_DEFAULTS: dict[str, PermissionDecision] = {
    "read_file": PermissionDecision.ALLOW,
    "search_web": PermissionDecision.ALLOW,
    "open_application": PermissionDecision.ALLOW,
    "type_text": PermissionDecision.ASK,
    "delete_file": PermissionDecision.ASK,
    "execute_shell": PermissionDecision.ASK,
    "install_software": PermissionDecision.ASK,
    "change_system_settings": PermissionDecision.ASK,
    "send_email": PermissionDecision.ASK,
    "upload_data": PermissionDecision.ASK,
    "access_camera": PermissionDecision.BLOCK,
    "access_microphone": PermissionDecision.BLOCK,
}


# ── WebSocket Event Types ──

class WSEventType(str, Enum):
    STATE_CHANGE = "state_change"
    AGENT_UPDATE = "agent_update"
    CHAT_MESSAGE = "chat_message"
    CHAT_STREAM = "chat_stream"
    SYSTEM_METRICS = "system_metrics"
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_RESPONSE = "permission_response"
    WORKFLOW_UPDATE = "workflow_update"
    ERROR = "error"
    NOTIFICATION = "notification"
