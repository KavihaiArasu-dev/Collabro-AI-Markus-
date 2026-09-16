/**
 * Markus AI — System Constants
 *
 * All enums, state definitions, risk levels, and routing constants used throughout the system.
 * Direct port from config/constants.py — preserving all logic exactly.
 */

// ── AI States (§6 of the design spec) ──

export enum AIState {
  IDLE = "idle",
  LISTENING = "listening",
  THINKING = "thinking",
  PLANNING = "planning",
  CODING = "coding",
  RESEARCH = "research",
  EXECUTING = "executing",
  WAITING_FOR_CONFIRMATION = "waiting_for_confirmation",
  SPEAKING = "speaking",
  SUCCESS = "success",
  WARNING = "warning",
  ERROR = "error",
}

// ── OmniRoute Routing Aliases (§6a) ──

export enum RouteAlias {
  AUTO = "auto/chat",
  FAST = "auto/fast",
  CODING = "auto/coding",
  CHEAP = "auto/cheap",
  OFFLINE = "auto/offline",
  SMART = "auto/smart",
}

// ── Provider Tiers (§6a) ──

export enum ProviderTier {
  TIER_A = "general_intelligence",
  TIER_B = "fast_intelligence",
  TIER_C = "local_intelligence",
}

// ── Intent Types (§4 — Intent Classifier) ──

export enum IntentType {
  CHAT = "chat",
  QUESTION = "question",
  SEARCH = "search",
  CODE = "code",
  DEBUG = "debug",
  FILE_OPERATION = "file_operation",
  APP_CONTROL = "app_control",
  SYSTEM_CONTROL = "system_control",
  BROWSER_AUTOMATION = "browser_automation",
  RESEARCH = "research",
  AUTOMATION = "automation",
  REVIEW = "review",
  ARCHITECTURE = "architecture",
  DOCUMENTATION = "documentation",
  TASK_MANAGEMENT = "task_management",
  MULTI_STEP_ACTION = "multi_step_action",
  MEMORY = "memory",
  RAG = "rag",
  SETTINGS = "settings",
  VOICE_COMMAND = "voice_command",
  YOUTUBE = "youtube",
}

// ── Tool Risk Levels (§11a) ──

export enum RiskLevel {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
}

// ── Permission Decisions (§11a) ──

export enum PermissionDecision {
  ALLOW = "allow",
  ASK = "ask",
  BLOCK = "block",
}

// ── Memory Categories (§6b) ──

export enum MemoryCategory {
  TEMPORARY = "temporary",
  SESSION = "session",
  PREFERENCE = "preference",
  PROJECT = "project",
  IMPORTANT = "important",
}

// ── Memory Types (§6b) ──

export enum MemoryType {
  SHORT_TERM = "short_term",
  EPISODIC = "episodic",
  PREFERENCE = "preference",
  PROJECT = "project",
}

// ── Agent Types (§5) ──

export enum AgentType {
  ORCHESTRATOR = "orchestrator",
  ARCHITECT = "architect",
  CODER = "coder",
  REVIEWER = "reviewer",
  DEBUGGER = "debugger",
  RESEARCHER = "researcher",
  DOCUMENTATION = "documentation",
  UI_UX = "ui_ux",
  AUTOMATION = "automation",
  MEMORY = "memory",
}

// ── Agent Status ──

export enum AgentStatus {
  IDLE = "idle",
  ACTIVE = "active",
  BUSY = "busy",
  ERROR = "error",
  DISABLED = "disabled",
}

// ── Agent default routing (§5 per-agent defaults) ──

export const AGENT_DEFAULT_ROUTES: Record<AgentType, RouteAlias> = {
  [AgentType.ORCHESTRATOR]: RouteAlias.AUTO,
  [AgentType.ARCHITECT]: RouteAlias.SMART,
  [AgentType.CODER]: RouteAlias.CODING,
  [AgentType.REVIEWER]: RouteAlias.CODING,
  [AgentType.DEBUGGER]: RouteAlias.SMART,
  [AgentType.RESEARCHER]: RouteAlias.AUTO,
  [AgentType.DOCUMENTATION]: RouteAlias.AUTO,
  [AgentType.UI_UX]: RouteAlias.AUTO,
  [AgentType.AUTOMATION]: RouteAlias.FAST,
  [AgentType.MEMORY]: RouteAlias.FAST,
};

// ── Model Profiles (§6a) ──

export const MODEL_PROFILES: Record<string, { route: RouteAlias; description: string }> = {
  normal: { route: RouteAlias.AUTO, description: "Normal conversation" },
  fast: { route: RouteAlias.FAST, description: "Fast answer" },
  coding: { route: RouteAlias.CODING, description: "Programming" },
  cheap: { route: RouteAlias.CHEAP, description: "Cost saving" },
  offline: { route: RouteAlias.OFFLINE, description: "Local/private" },
  smart: { route: RouteAlias.SMART, description: "Adaptive reasoning" },
};

// ── Permission Defaults (§11a) — Administrator Mode Enabled ──

export const PERMISSION_DEFAULTS: Record<string, PermissionDecision> = {
  read_file: PermissionDecision.ALLOW,
  write_file: PermissionDecision.ALLOW,
  list_directory: PermissionDecision.ALLOW,
  delete_file: PermissionDecision.ALLOW,
  execute_shell: PermissionDecision.ALLOW,
  execute_command: PermissionDecision.ALLOW,
  run_dev_command: PermissionDecision.ALLOW,
  search_web: PermissionDecision.ALLOW,
  open_app: PermissionDecision.ALLOW,
  open_application: PermissionDecision.ALLOW,
  close_app: PermissionDecision.ALLOW,
  close_application: PermissionDecision.ALLOW,
  focus_app: PermissionDecision.ALLOW,
  list_running_apps: PermissionDecision.ALLOW,
  browser_open: PermissionDecision.ALLOW,
  browser_search: PermissionDecision.ALLOW,
  youtube_search: PermissionDecision.ALLOW,
  youtube_play: PermissionDecision.ALLOW,
  set_volume: PermissionDecision.ALLOW,
  set_brightness: PermissionDecision.ALLOW,
  take_screenshot: PermissionDecision.ALLOW,
  type_text: PermissionDecision.ALLOW,
  install_software: PermissionDecision.ALLOW,
  change_system_settings: PermissionDecision.ALLOW,
  send_email: PermissionDecision.ALLOW,
  upload_data: PermissionDecision.ALLOW,
  access_camera: PermissionDecision.ALLOW,
  access_microphone: PermissionDecision.ALLOW,
  system_info: PermissionDecision.ALLOW,
};

// ── WebSocket Event Types ──

export enum WSEventType {
  STATE_CHANGE = "state_change",
  AGENT_UPDATE = "agent_update",
  CHAT_MESSAGE = "chat_message",
  CHAT_STREAM = "chat_stream",
  SYSTEM_METRICS = "system_metrics",
  PERMISSION_REQUEST = "permission_request",
  PERMISSION_RESPONSE = "permission_response",
  WORKFLOW_UPDATE = "workflow_update",
  ERROR = "error",
  NOTIFICATION = "notification",
}
