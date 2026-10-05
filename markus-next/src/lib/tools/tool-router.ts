/**
 * Markus AI — Tool Registry & Router (§11a)
 *
 * Deterministic tools for deterministic work. Every tool execution flows through:
 * 1. Look up tool definition
 * 2. Check permissions via Permission Manager
 * 3. If allowed, execute via deterministic handler
 * 4. Return result
 *
 * Direct port from tools/tool_router.py — preserving all tool handlers.
 */

import { exec, execFile } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { RiskLevel, PermissionDecision } from "@/lib/config/constants";
import { permissionManager } from "@/lib/security/permissions";
import { createExecutionResult, type ExecutionResult, type PostCondition } from "./contracts";

interface ToolDefinition {
  name: string;
  description: string;
  riskLevel: RiskLevel;
  handler: (args: Record<string, string>) => Promise<ExecutionResult>;
  arguments: Record<string, string>;
  timeout: number;
  requiresConfirmation: boolean;
  postConditions: PostCondition[];
}

// ── Web Application & Website Target Registry ──
const WEB_TARGETS: Record<string, string> = {
  youtube: "https://www.youtube.com",
  yt: "https://www.youtube.com",
  google: "https://www.google.com",
  chatgpt: "https://chatgpt.com",
  claude: "https://claude.ai",
  gemini: "https://gemini.google.com",
  perplexity: "https://www.perplexity.ai",
  duckduckgo: "https://duckduckgo.com",
  github: "https://github.com",
  gitlab: "https://gitlab.com",
  reddit: "https://www.reddit.com",
  twitter: "https://x.com",
  x: "https://x.com",
  linkedin: "https://www.linkedin.com",
  instagram: "https://www.instagram.com",
  facebook: "https://www.facebook.com",
  threads: "https://www.threads.net",
  gmail: "https://mail.google.com",
  netflix: "https://www.netflix.com",
  spotify: "https://open.spotify.com",
  "spotify web": "https://open.spotify.com",
  whatsapp: "https://web.whatsapp.com",
  discord: "https://discord.com/app",
  stackoverflow: "https://stackoverflow.com",
  huggingface: "https://huggingface.co",
  amazon: "https://www.amazon.com",
  wikipedia: "https://www.wikipedia.org",
  twitch: "https://www.twitch.tv",
};

// ── Native Application Aliases (Windows) ──
const APP_ALIASES: Record<string, string> = {
  chrome: "chrome",
  "google chrome": "chrome",
  firefox: "firefox",
  edge: "msedge",
  msedge: "msedge",
  brave: "brave",
  code: "code",
  vscode: "code",
  "vs code": "code",
  notepad: "notepad",
  calc: "calc",
  calculator: "calc",
  explorer: "explorer",
  "file explorer": "explorer",
  terminal: "wt",
  powershell: "powershell",
  cmd: "cmd",
  spotify: "spotify",
  discord: "discord",
  whatsapp: "whatsapp",
  paint: "mspaint",
  settings: "ms-settings:",
  taskmanager: "taskmgr",
  "task manager": "taskmgr",
};

class ToolRouter {
  private _tools: Map<string, ToolDefinition> = new Map();

  constructor() {
    this._registerBuiltinTools();
    console.log(`Tool Router initialized with ${this._tools.size} tools`);
  }

  register(tool: ToolDefinition): void {
    this._tools.set(tool.name, tool);
  }

  async execute(toolName: string, args: Record<string, string>): Promise<Record<string, unknown>> {
    const tool = this._tools.get(toolName);
    if (!tool) {
      return { success: false, error: `Unknown tool: ${toolName}` };
    }

    // Permission check
    const permResult = permissionManager.checkPermission(
      toolName,
      toolName,
      args,
      tool.riskLevel,
      "tool_router",
      tool.description,
    );

    if (permResult.decision === PermissionDecision.BLOCK) {
      return { success: false, error: `Permission blocked for: ${toolName}` };
    }

    if (permResult.decision === PermissionDecision.ASK) {
      return {
        success: false,
        needs_confirmation: true,
        permission_id: permResult.id,
        action: toolName,
        description: tool.description,
      };
    }

    // Execute tool
    const start = performance.now();
    try {
      const result = await tool.handler(args);
      result.executionTimeMs = performance.now() - start;
      return { success: true, result: result.data, execution_time_ms: result.executionTimeMs };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  listTools(): Record<string, unknown>[] {
    return Array.from(this._tools.values()).map((t) => ({
      name: t.name,
      description: t.description,
      risk_level: t.riskLevel,
      arguments: t.arguments,
      requires_confirmation: t.requiresConfirmation,
    }));
  }

  private _registerBuiltinTools(): void {
    // ── File Tools ──
    this.register({
      name: "read_file",
      description: "Read the contents of a file",
      riskLevel: RiskLevel.LOW,
      handler: this._readFile.bind(this),
      arguments: { path: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "write_file",
      description: "Write content to a file",
      riskLevel: RiskLevel.MEDIUM,
      handler: this._writeFile.bind(this),
      arguments: { path: "string", content: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [{ assertionType: "file_exists", targetParam: "path", timeout: 1.5 }],
    });

    this.register({
      name: "list_directory",
      description: "List files and folders in a directory",
      riskLevel: RiskLevel.LOW,
      handler: this._listDirectory.bind(this),
      arguments: { path: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "delete_file",
      description: "Delete a file",
      riskLevel: RiskLevel.HIGH,
      handler: this._deleteFile.bind(this),
      arguments: { path: "string" },
      timeout: 30,
      requiresConfirmation: true,
      postConditions: [],
    });

    // ── Shell Tools ──
    this.register({
      name: "execute_shell",
      description: "Execute a shell command",
      riskLevel: RiskLevel.LOW,
      handler: this._executeShell.bind(this),
      arguments: { command: "string" },
      timeout: 60,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "execute_command",
      description: "Execute a shell command (alias for execute_shell)",
      riskLevel: RiskLevel.LOW,
      handler: this._executeShell.bind(this),
      arguments: { command: "string" },
      timeout: 60,
      requiresConfirmation: false,
      postConditions: [],
    });

    // ── Desktop App & Web Navigation Tools (Administrator System Access) ──
    this.register({
      name: "open_app",
      description: "Open an application or website by name (e.g. chrome, youtube, vscode, spotify, notepad, github)",
      riskLevel: RiskLevel.LOW,
      handler: this._openApp.bind(this),
      arguments: { app_name: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "open_application",
      description: "Open an application or website (alias for open_app)",
      riskLevel: RiskLevel.LOW,
      handler: this._openApp.bind(this),
      arguments: { app_name: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "close_app",
      description: "Close/terminate an application by name",
      riskLevel: RiskLevel.LOW,
      handler: this._closeApp.bind(this),
      arguments: { app_name: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "close_application",
      description: "Close/terminate an application (alias for close_app)",
      riskLevel: RiskLevel.LOW,
      handler: this._closeApp.bind(this),
      arguments: { app_name: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "browser_open",
      description: "Open a URL in the default web browser",
      riskLevel: RiskLevel.LOW,
      handler: this._browserOpen.bind(this),
      arguments: { url: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "open_url",
      description: "Open a URL in default browser (alias for browser_open)",
      riskLevel: RiskLevel.LOW,
      handler: this._browserOpen.bind(this),
      arguments: { url: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "browser_search",
      description: "Search Google / web in default browser",
      riskLevel: RiskLevel.LOW,
      handler: this._browserSearch.bind(this),
      arguments: { query: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "youtube_play",
      description: "Search and play a video or song on YouTube in browser",
      riskLevel: RiskLevel.LOW,
      handler: this._youtubePlay.bind(this),
      arguments: { query: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "youtube_search",
      description: "Search for videos on YouTube",
      riskLevel: RiskLevel.LOW,
      handler: this._youtubePlay.bind(this),
      arguments: { query: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "list_running_apps",
      description: "List currently running user applications and processes",
      riskLevel: RiskLevel.LOW,
      handler: this._listRunningApps.bind(this),
      arguments: {},
      timeout: 15,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "take_screenshot",
      description: "Capture screen and save screenshot to Desktop",
      riskLevel: RiskLevel.LOW,
      handler: this._takeScreenshot.bind(this),
      arguments: {},
      timeout: 15,
      requiresConfirmation: false,
      postConditions: [],
    });

    // ── System Tools ──
    this.register({
      name: "system_info",
      description: "Get system information (CPU, RAM, disk, OS)",
      riskLevel: RiskLevel.LOW,
      handler: this._systemInfo.bind(this),
      arguments: {},
      timeout: 10,
      requiresConfirmation: false,
      postConditions: [],
    });

    this.register({
      name: "search_web",
      description: "Search the web for a query",
      riskLevel: RiskLevel.LOW,
      handler: this._searchWeb.bind(this),
      arguments: { query: "string" },
      timeout: 30,
      requiresConfirmation: false,
      postConditions: [],
    });
  }

  // ── Tool Handlers ──

  private async _readFile(args: Record<string, string>): Promise<ExecutionResult> {
    const filePath = args.path;
    if (!filePath) return createExecutionResult({ success: false, error: "Path is required" });

    try {
      const content = fs.readFileSync(filePath, "utf-8");
      return createExecutionResult({
        success: true,
        data: { content, path: filePath, size: content.length },
        outputMessage: `Read ${content.length} characters from ${filePath}`,
      });
    } catch (e) {
      return createExecutionResult({ success: false, error: `Failed to read file: ${e}` });
    }
  }

  private async _writeFile(args: Record<string, string>): Promise<ExecutionResult> {
    const filePath = args.path;
    const content = args.content;
    if (!filePath || content === undefined) {
      return createExecutionResult({ success: false, error: "Path and content are required" });
    }

    try {
      const dir = path.dirname(filePath);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(filePath, content, "utf-8");
      return createExecutionResult({
        success: true,
        data: { path: filePath, bytes_written: content.length },
        outputMessage: `Written ${content.length} characters to ${filePath}`,
      });
    } catch (e) {
      return createExecutionResult({ success: false, error: `Failed to write file: ${e}` });
    }
  }

  private async _listDirectory(args: Record<string, string>): Promise<ExecutionResult> {
    const dirPath = args.path || ".";
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      const items = entries.map((e) => ({
        name: e.name,
        type: e.isDirectory() ? "directory" : "file",
        size: e.isFile() ? fs.statSync(path.join(dirPath, e.name)).size : null,
      }));
      return createExecutionResult({
        success: true,
        data: { path: dirPath, entries: items, count: items.length },
        outputMessage: `Found ${items.length} items in ${dirPath}`,
      });
    } catch (e) {
      return createExecutionResult({ success: false, error: `Failed to list directory: ${e}` });
    }
  }

  private async _deleteFile(args: Record<string, string>): Promise<ExecutionResult> {
    const filePath = args.path;
    if (!filePath) return createExecutionResult({ success: false, error: "Path is required" });

    try {
      fs.unlinkSync(filePath);
      return createExecutionResult({
        success: true,
        data: { path: filePath },
        outputMessage: `Deleted ${filePath}`,
      });
    } catch (e) {
      return createExecutionResult({ success: false, error: `Failed to delete file: ${e}` });
    }
  }

  private async _executeShell(args: Record<string, string>): Promise<ExecutionResult> {
    const command = args.command;
    if (!command) return createExecutionResult({ success: false, error: "Command is required" });

    return new Promise((resolve) => {
      exec(command, { timeout: 60000 }, (error, stdout, stderr) => {
        if (error) {
          resolve(createExecutionResult({
            success: false,
            data: { stdout, stderr },
            error: `Command failed: ${error.message}`,
          }));
        } else {
          resolve(createExecutionResult({
            success: true,
            data: { stdout, stderr, exit_code: 0 },
            outputMessage: stdout.slice(0, 500),
          }));
        }
      });
    });
  }

  private async _systemInfo(): Promise<ExecutionResult> {
    try {
      const info = {
        platform: os.platform(),
        arch: os.arch(),
        hostname: os.hostname(),
        cpus: os.cpus().length,
        total_memory_gb: Math.round((os.totalmem() / (1024 ** 3)) * 100) / 100,
        free_memory_gb: Math.round((os.freemem() / (1024 ** 3)) * 100) / 100,
        uptime_hours: Math.round((os.uptime() / 3600) * 100) / 100,
        home_dir: os.homedir(),
      };
      return createExecutionResult({
        success: true,
        data: info,
        outputMessage: `System: ${info.platform} ${info.arch}, ${info.cpus} CPUs, ${info.total_memory_gb}GB RAM`,
      });
    } catch (e) {
      return createExecutionResult({ success: false, error: `Failed to get system info: ${e}` });
    }
  }

  private async _openApp(args: Record<string, string>): Promise<ExecutionResult> {
    const rawName = (args.app_name || args.name || "").trim();
    if (!rawName) return createExecutionResult({ success: false, error: "App or website name is required" });
    const nameLower = rawName.toLowerCase();

    // 1. Direct URL or Web Target
    if (rawName.startsWith("http://") || rawName.startsWith("https://")) {
      return this._browserOpen({ url: rawName });
    }
    if (WEB_TARGETS[nameLower]) {
      const targetUrl = WEB_TARGETS[nameLower];
      return this._browserOpen({ url: targetUrl });
    }

    // 2. Desktop Application on Windows / macOS / Linux
    const isWin = os.platform() === "win32";
    const appCmd = APP_ALIASES[nameLower] || rawName;

    return new Promise((resolve) => {
      let command = `start "" "${appCmd}"`;
      if (!isWin) {
        command = os.platform() === "darwin" ? `open -a "${appCmd}"` : `xdg-open "${appCmd}" &`;
      }
      exec(command, (error) => {
        if (error) {
          // Fallback: try powershell Start-Process
          if (isWin) {
            exec(`powershell -Command "Start-Process '${appCmd}'"`, (psErr) => {
              if (psErr) {
                resolve(createExecutionResult({
                  success: false,
                  error: `Could not launch ${rawName}: ${psErr.message}`,
                }));
              } else {
                resolve(createExecutionResult({
                  success: true,
                  data: { app: rawName, command: appCmd },
                  outputMessage: `Launched ${rawName} successfully`,
                }));
              }
            });
            return;
          }
          resolve(createExecutionResult({
            success: false,
            error: `Could not launch ${rawName}: ${error.message}`,
          }));
        } else {
          resolve(createExecutionResult({
            success: true,
            data: { app: rawName, command: appCmd },
            outputMessage: `Launched ${rawName} successfully`,
          }));
        }
      });
    });
  }

  private async _closeApp(args: Record<string, string>): Promise<ExecutionResult> {
    const rawName = (args.app_name || args.name || "").trim();
    if (!rawName) return createExecutionResult({ success: false, error: "App name is required" });
    const isWin = os.platform() === "win32";
    const appTarget = APP_ALIASES[rawName.toLowerCase()] || rawName;

    return new Promise((resolve) => {
      const command = isWin ? `taskkill /IM "${appTarget}*.exe" /F` : `pkill -f "${appTarget}"`;
      exec(command, (error, stdout, stderr) => {
        resolve(createExecutionResult({
          success: true,
          data: { app: rawName, output: stdout || stderr },
          outputMessage: `Terminated ${rawName}`,
        }));
      });
    });
  }

  private async _browserOpen(args: Record<string, string>): Promise<ExecutionResult> {
    let url = (args.url || "").trim();
    if (!url) return createExecutionResult({ success: false, error: "URL is required" });
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = "https://" + url;
    }
    const isWin = os.platform() === "win32";
    const command = isWin ? `start "" "${url}"` : (os.platform() === "darwin" ? `open "${url}"` : `xdg-open "${url}" &`);

    return new Promise((resolve) => {
      exec(command, (error) => {
        if (error) {
          resolve(createExecutionResult({ success: false, error: `Failed to open ${url}: ${error.message}` }));
        } else {
          resolve(createExecutionResult({
            success: true,
            data: { url },
            outputMessage: `Opened ${url} in default browser`,
          }));
        }
      });
    });
  }

  private async _browserSearch(args: Record<string, string>): Promise<ExecutionResult> {
    const query = (args.query || "").trim();
    if (!query) return createExecutionResult({ success: false, error: "Query is required" });
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
    return this._browserOpen({ url: searchUrl });
  }

  private async _youtubePlay(args: Record<string, string>): Promise<ExecutionResult> {
    const query = (args.query || "").trim();
    if (!query) return createExecutionResult({ success: false, error: "Query is required" });
    const ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
    return this._browserOpen({ url: ytUrl });
  }

  private async _listRunningApps(): Promise<ExecutionResult> {
    const isWin = os.platform() === "win32";
    return new Promise((resolve) => {
      const command = isWin ? "tasklist /FO CSV /NH" : "ps -eo comm";
      exec(command, { maxBuffer: 1024 * 1024 * 5 }, (error, stdout) => {
        if (error) {
          resolve(createExecutionResult({ success: false, error: error.message }));
          return;
        }
        const processes = stdout
          .split("\n")
          .map((line) => line.replace(/"/g, "").split(",")[0].trim())
          .filter((p) => p && !p.startsWith("svchost") && !p.startsWith("System") && !p.startsWith("conhost"));
        const unique = Array.from(new Set(processes)).slice(0, 40);
        resolve(createExecutionResult({
          success: true,
          data: { count: unique.length, processes: unique },
          outputMessage: `Found ${unique.length} running user processes`,
        }));
      });
    });
  }

  private async _takeScreenshot(): Promise<ExecutionResult> {
    const isWin = os.platform() === "win32";
    if (!isWin) {
      return createExecutionResult({ success: false, error: "Screenshot currently supported on Windows" });
    }
    const desktopPath = path.join(os.homedir(), "Desktop");
    const filename = `screenshot_${Date.now()}.png`;
    const filePath = path.join(desktopPath, filename);

    return new Promise((resolve) => {
      const psScript = `Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $s = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $b = New-Object System.Drawing.Bitmap $s.Width, $s.Height; $g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($s.Location, [System.Drawing.Point]::Empty, $s.Size); $b.Save('${filePath.replace(/\\/g, "\\\\")}', [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $b.Dispose();`;

      execFile("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", psScript], (error) => {
        if (error) {
          resolve(createExecutionResult({ success: false, error: `Failed to capture screenshot: ${error.message}` }));
        } else {
          resolve(createExecutionResult({
            success: true,
            data: { path: filePath },
            outputMessage: `Screenshot saved to Desktop: ${filename}`,
          }));
        }
      });
    });
  }

  private async _searchWeb(args: Record<string, string>): Promise<ExecutionResult> {
    const query = args.query;
    if (!query) return createExecutionResult({ success: false, error: "Query is required" });

    return this._browserSearch({ query });
  }
}

// Singleton
export const toolRouter = new ToolRouter();
