/**
 * Markus AI — Specialized Agent Implementations (§5)
 *
 * Each agent has a dedicated responsibility and a default OmniRoute route.
 * Direct port from agents/implementations.py — preserving all system prompts exactly.
 */

import { AgentType } from "@/lib/config/constants";
import { BaseAgent } from "./base-agent";
import { toolRouter } from "@/lib/tools/tool-router";

export class CoderAgent extends BaseAgent {
  constructor() {
    super(AgentType.CODER);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Coder Agent — an expert software engineer. " +
      "You write clean, efficient, well-documented code. " +
      "You support Python, TypeScript, JavaScript, React, Next.js, Node, Rust, Go, Java, and more. " +
      "Always follow best practices: proper error handling, type hints, tests, clear naming. " +
      "When writing code, include comments explaining complex logic. " +
      "If refactoring, explain what changed and why."
    );
  }
}

export class ArchitectAgent extends BaseAgent {
  constructor() {
    super(AgentType.ARCHITECT);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Architect Agent — a senior software architect. " +
      "You design scalable, maintainable systems following Clean Architecture principles. " +
      "You create project structures, API designs, database schemas, and system diagrams. " +
      "Always consider: separation of concerns, dependency injection, extensibility, " +
      "performance, and security. Explain your architectural decisions clearly."
    );
  }
}

export class ReviewerAgent extends BaseAgent {
  constructor() {
    super(AgentType.REVIEWER);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Reviewer Agent — a meticulous code reviewer. " +
      "You perform thorough code reviews covering: correctness, security vulnerabilities, " +
      "performance issues, code style, architecture compliance, test coverage, " +
      "and maintainability. Rate severity of issues (critical/warning/info). " +
      "Always provide specific, actionable feedback with code suggestions."
    );
  }
}

export class DebugAgent extends BaseAgent {
  constructor() {
    super(AgentType.DEBUGGER);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Debug Agent — an expert debugger. " +
      "You analyze error messages, stack traces, runtime errors, memory leaks, " +
      "and dependency issues. You identify root causes methodically. " +
      "Always explain: what went wrong, why it happened, and how to fix it. " +
      "Provide step-by-step debugging strategies when the cause isn't immediately clear."
    );
  }
}

export class ResearchAgent extends BaseAgent {
  constructor() {
    super(AgentType.RESEARCHER);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's General Knowledge & Research Agent — an intelligent, articulate, and versatile assistant. " +
      "You answer any user question across general knowledge, science, history, geography, mathematics, philosophy, " +
      "creators/developers, architecture, libraries, frameworks, APIs, and everyday topics. " +
      "Always provide clear, thorough, well-structured, and helpful explanations. " +
      "When technical or domain-specific concepts arise, provide practical examples and intuitive explanations."
    );
  }
}

export class DocumentationAgent extends BaseAgent {
  constructor() {
    super(AgentType.DOCUMENTATION);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Documentation Agent — a technical writer. " +
      "You create clear, comprehensive documentation: READMEs, API docs, " +
      "architecture docs, developer guides, and technical reports. " +
      "Use proper markdown formatting, include code examples, " +
      "and organize content with clear headings and sections."
    );
  }
}

export class UIUXAgent extends BaseAgent {
  constructor() {
    super(AgentType.UI_UX);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's UI/UX Agent — a design specialist. " +
      "You design interfaces, design systems, components, and user flows. " +
      "You prioritize: accessibility, responsive design, visual hierarchy, " +
      "and modern aesthetics. Provide specific CSS/component implementations " +
      "when asked, following the Markus design system."
    );
  }
}

export class AutomationAgent extends BaseAgent {
  constructor() {
    super(AgentType.AUTOMATION);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Automation Agent — a workflow and desktop automation specialist. " +
      "You have full administrator permissions to control apps, websites, system settings, " +
      "and workflows. You interpret commands precisely and execute them directly via the Tool Router."
    );
  }

  override async process(userInput: string, context?: Record<string, unknown>): Promise<string> {
    const direct = await this._handleDirectAction(userInput);
    if (direct !== null) return direct;
    return super.process(userInput, context);
  }

  override async *processStream(
    userInput: string,
    context?: Record<string, unknown>,
  ): AsyncGenerator<string> {
    const direct = await this._handleDirectAction(userInput);
    if (direct !== null) {
      yield direct;
      return;
    }
    yield* super.processStream(userInput, context);
  }

  private async _handleDirectAction(input: string): Promise<string | null> {
    const trimmed = input.trim();
    const lower = trimmed.toLowerCase();

    // 1. Open app or website
    const openMatch = lower.match(/^(?:open|launch|start|run)\s+(.+)$/i);
    if (openMatch) {
      const target = openMatch[1].trim();
      const res = await toolRouter.execute("open_app", { app_name: target });
      if (res.success) {
        return `🚀 Launched **${target}** with administrator permissions.`;
      }
      return `❌ Failed to launch ${target}: ${res.error}`;
    }

    // 2. Close app
    const closeMatch = lower.match(/^(?:close|quit|kill|stop|terminate)\s+(.+)$/i);
    if (closeMatch) {
      const target = closeMatch[1].trim();
      const res = await toolRouter.execute("close_app", { app_name: target });
      if (res.success) {
        return `🛑 Terminated application: **${target}**.`;
      }
      return `❌ Failed to terminate application ${target}: ${res.error}`;
    }

    // 3. YouTube play / search
    const ytMatch = lower.match(/^(?:play|youtube)\s+(.+)$/i) || lower.match(/^(?:play|listen to)\s+(.+)\s+on\s+youtube$/i);
    if (ytMatch) {
      const query = ytMatch[1].trim();
      await toolRouter.execute("youtube_play", { query });
      return `▶️ Searching and playing **"${query}"** on YouTube in your browser.`;
    }

    // 4. Browser search / Google
    const searchMatch = lower.match(/^(?:google|search|browse|web search)\s+(.+)$/i);
    if (searchMatch) {
      const query = searchMatch[1].trim();
      await toolRouter.execute("browser_search", { query });
      return `🔍 Opened web search for **"${query}"** in your browser.`;
    }

    // 5. Screenshot
    if (lower.includes("screenshot") || lower.includes("capture screen")) {
      const res = await toolRouter.execute("take_screenshot", {});
      if (res.success) {
        return `📸 Screenshot captured and saved to your Desktop.`;
      }
      return `❌ Screenshot failed: ${res.error}`;
    }

    // 6. Running apps
    if (lower.includes("running apps") || lower.includes("list apps") || lower.includes("list processes")) {
      const res = await toolRouter.execute("list_running_apps", {});
      if (res.success && res.result) {
        const data = res.result as { count: number; processes: string[] };
        return `💻 Currently running user applications (${data.count}):\n\n${data.processes.slice(0, 15).map((p) => `• \`${p}\``).join("\n")}`;
      }
    }

    return null;
  }
}

export class MemoryAgent extends BaseAgent {
  constructor() {
    super(AgentType.MEMORY);
  }

  get systemPrompt(): string {
    return (
      "You are Markus's Memory Agent — responsible for context management. " +
      "You maintain conversation history, project context, coding preferences, " +
      "and architecture knowledge. You decide what to remember and what to forget. " +
      "Tag memories with appropriate categories: TEMPORARY, SESSION, PREFERENCE, " +
      "PROJECT, IMPORTANT. Never persist sensitive data without explicit approval."
    );
  }
}
