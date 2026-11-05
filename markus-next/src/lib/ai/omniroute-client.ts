/**
 * Markus AI — OmniRoute Client (§6a)
 *
 * Primary AI execution engine backed by AIServer (agy --dangerously-skip-permissions)
 * with graceful fallback to OpenAI/Gemini providers.
 */

import OpenAI from "openai";
import { settings } from "@/lib/config/settings";
import { queryAIServer, checkAIServerStatus } from "@/lib/ai/ai-server-client";

class OmniRouteClient {
  private _baseUrl: string;
  private _apiKey: string;
  private _timeout: number;
  private _maxRetries: number;
  private _connected: boolean = true;
  private _activeProvider: string = "AIServer (agy)";
  private _activeModel: string = "agy-engine";
  private _cachedClient: OpenAI | null = null;
  private _cachedClientKey: string = "";

  constructor() {
    this._baseUrl = process.env.OMNIROUTE_BASE_URL ?? settings.omniroute.baseUrl;
    this._apiKey = process.env.OMNIROUTE_API_KEY ?? settings.omniroute.apiKey ?? "no-key";
    this._timeout = settings.omniroute.timeout;
    this._maxRetries = settings.omniroute.maxRetries;
    console.log(`OmniRoute client initialized with primary engine: AIServer (agy)`);
  }

  private _buildPromptForAIServer(
    messages: Array<{ role: string; content: string }>,
    systemPrompt?: string,
  ): string {
    const parts: string[] = [];
    if (systemPrompt) {
      parts.push(`SYSTEM INSTRUCTIONS:\n${systemPrompt}`);
    }
    for (const msg of messages) {
      if (msg.role === "system") {
        parts.push(`SYSTEM:\n${msg.content}`);
      } else if (msg.role === "assistant") {
        parts.push(`ASSISTANT:\n${msg.content}`);
      } else {
        parts.push(`USER:\n${msg.content}`);
      }
    }
    return parts.join("\n\n");
  }

  /**
   * Determine available AI provider endpoint in order of preference:
   * 1. OmniRoute Gateway (if reachable)
   * 2. Gemini API Key
   * 3. Groq API Key
   * 4. OpenAI API Key
   * 5. Local Ollama
   */
  private _resolveBestEndpoint(): [string, string, string] {
    const geminiKey = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
    const groqKey = process.env.GROQ_API_KEY;
    const openaiKey = process.env.OPENAI_API_KEY;
    const ollamaUrl = process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";

    if (this._connected) {
      return [this._baseUrl, this._apiKey, "auto"];
    }
    if (geminiKey) {
      return ["https://generativelanguage.googleapis.com/v1beta/openai/", geminiKey, "gemini-1.5-flash"];
    }
    if (groqKey) {
      return ["https://api.groq.com/openai/v1", groqKey, "llama-3.3-70b-versatile"];
    }
    if (openaiKey) {
      return ["https://api.openai.com/v1", openaiKey, "gpt-4o-mini"];
    }
    if (process.env.USE_OLLAMA === "true") {
      return [ollamaUrl, "ollama", "llama3"];
    }

    return [this._baseUrl, this._apiKey, "auto"];
  }

  private _getClient(): [OpenAI, string] {
    const [baseUrl, apiKey, defaultModel] = this._resolveBestEndpoint();
    const key = `${baseUrl}::${apiKey}::${this._timeout}::${this._maxRetries}`;
    if (!this._cachedClient || this._cachedClientKey !== key) {
      this._cachedClient = new OpenAI({
        baseURL: baseUrl,
        apiKey: apiKey,
        timeout: this._timeout * 1000,
        maxRetries: this._maxRetries,
      });
      this._cachedClientKey = key;
    }
    return [this._cachedClient, defaultModel];
  }

  /**
   * Generate a non-streaming response via Gemini REST API (direct fallback).
   */
  private async _generateGemini(
    messages: Array<{ role: string; content: string }>,
    temperature: number = 0.7,
    maxTokens: number = 4096,
    systemPrompt?: string,
  ): Promise<string> {
    const geminiKey = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
    if (!geminiKey) {
      throw new Error("GEMINI_API_KEY is not configured and AIServer was unavailable.");
    }

    const models = [
      process.env.GEMINI_MODEL ?? "gemini-3.1-flash-lite",
      "gemini-3.5-flash-lite",
      "gemini-3.6-flash",
      "gemini-flash-latest",
    ];
    const payload = this._formatGeminiPayload(messages, systemPrompt, temperature, maxTokens);

    let lastError: string | null = null;
    for (const model of models) {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${geminiKey}`;
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(15000),
        });
        if (res.ok) {
          const data = await res.json();
          const candidates = data.candidates ?? [];
          if (candidates.length > 0 && candidates[0].content) {
            const parts = candidates[0].content.parts ?? [];
            const text = parts.map((p: { text?: string }) => p.text ?? "").join("");
            if (text) {
              this._activeProvider = "gemini";
              this._activeModel = model;
              this._connected = true;
              return text;
            }
          }
        } else {
          const body = await res.text();
          lastError = `Gemini ${model} returned HTTP ${res.status}: ${body.slice(0, 200)}`;
          console.warn(lastError);
        }
      } catch (err) {
        lastError = String(err);
        console.warn(`Gemini ${model} request failed: ${err}`);
      }
    }

    throw new Error(`All Gemini models failed. Last error: ${lastError}`);
  }

  /**
   * Generate a streaming response via Gemini REST API (direct fallback).
   */
  private async *_generateGeminiStream(
    messages: Array<{ role: string; content: string }>,
    temperature: number = 0.7,
    maxTokens: number = 4096,
    systemPrompt?: string,
  ): AsyncGenerator<string> {
    const geminiKey = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
    if (!geminiKey) {
      throw new Error("GEMINI_API_KEY is not configured and AIServer was unavailable.");
    }

    const models = [
      process.env.GEMINI_MODEL ?? "gemini-3.1-flash-lite",
      "gemini-3.5-flash-lite",
      "gemini-3.6-flash",
      "gemini-flash-latest",
    ];
    const payload = this._formatGeminiPayload(messages, systemPrompt, temperature, maxTokens);

    let lastError: string | null = null;
    for (const model of models) {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse&key=${geminiKey}`;
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const body = await res.text();
          lastError = `Gemini ${model} returned HTTP ${res.status}: ${body.slice(0, 200)}`;
          console.warn(lastError);
          continue;
        }

        this._activeProvider = "gemini";
        this._activeModel = model;
        this._connected = true;

        const reader = res.body?.getReader();
        if (!reader) continue;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              try {
                const parsed = JSON.parse(jsonStr);
                const candidates = parsed.candidates ?? [];
                if (candidates.length > 0 && candidates[0].content) {
                  const parts = candidates[0].content.parts ?? [];
                  for (const part of parts) {
                    if (part.text) {
                      yield part.text;
                    }
                  }
                }
              } catch {
                // Skip malformed JSON lines
              }
            }
          }
        }
        return; // Successfully streamed
      } catch (err) {
        lastError = String(err);
        console.warn(`Gemini ${model} stream failed: ${err}`);
      }
    }

    throw new Error(`All Gemini streaming models failed. Last error: ${lastError}`);
  }

  private _formatGeminiPayload(
    messages: Array<{ role: string; content: string }>,
    systemPrompt?: string,
    temperature: number = 0.7,
    maxTokens: number = 4096,
  ): Record<string, unknown> {
    const contents: Array<{ role: string; parts: Array<{ text: string }> }> = [];
    const sysParts: string[] = [];

    if (systemPrompt) {
      sysParts.push(systemPrompt);
    }

    for (const msg of messages) {
      if (msg.role === "system") {
        sysParts.push(msg.content);
      } else if (msg.role === "assistant") {
        contents.push({ role: "model", parts: [{ text: msg.content }] });
      } else {
        contents.push({ role: "user", parts: [{ text: msg.content }] });
      }
    }

    if (contents.length === 0) {
      contents.push({ role: "user", parts: [{ text: "Hello" }] });
    }

    const payload: Record<string, unknown> = {
      contents,
      generationConfig: { temperature, maxOutputTokens: maxTokens },
    };

    if (sysParts.length > 0) {
      payload.systemInstruction = { parts: [{ text: sysParts.join("\n\n") }] };
    }

    return payload;
  }

  /**
   * Primary generator: routes every query to AIServer (agy) first.
   */
  async generate(
    messages: Array<{ role: string; content: string }>,
    route: string = "auto",
    temperature: number = 0.7,
    maxTokens: number = 4096,
    systemPrompt?: string,
  ): Promise<string> {
    const prompt = this._buildPromptForAIServer(messages, systemPrompt);
    console.log(`[OmniRouteClient] Passing question to AIServer (agy)...`);

    try {
      const response = await queryAIServer(prompt);
      if (response && response.trim().length > 0) {
        this._activeProvider = "AIServer (agy)";
        this._activeModel = "agy-engine";
        this._connected = true;
        return response;
      }
    } catch (err) {
      console.warn(`[OmniRouteClient] AIServer query failed: ${err}`);
    }

    // Secondary fallback: Try OpenAI-compatible client
    try {
      const allMessages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [];
      if (systemPrompt) {
        allMessages.push({ role: "system", content: systemPrompt });
      }
      for (const msg of messages) {
        allMessages.push({
          role: msg.role as "system" | "user" | "assistant",
          content: msg.content,
        });
      }
      const [client, defaultModel] = this._getClient();
      const response = await client.chat.completions.create({
        model: route || defaultModel,
        messages: allMessages,
        temperature,
        max_tokens: maxTokens,
      });

      const content = response.choices?.[0]?.message?.content;
      if (content) {
        this._connected = true;
        return content;
      }
    } catch (err) {
      console.warn(`OpenAI-compatible request failed: ${err}`);
    }

    // Tertiary fallback: direct Gemini
    return this._generateGemini(messages, temperature, maxTokens, systemPrompt);
  }

  /**
   * Primary stream generator: queries AIServer (agy) and streams the answer chunks.
   */
  async *generateStream(
    messages: Array<{ role: string; content: string }>,
    route: string = "auto",
    temperature: number = 0.7,
    maxTokens: number = 4096,
    systemPrompt?: string,
  ): AsyncGenerator<string> {
    const prompt = this._buildPromptForAIServer(messages, systemPrompt);
    console.log(`[OmniRouteClient] Passing question to AIServer (agy) stream...`);

    try {
      const response = await queryAIServer(prompt);
      if (response && response.trim().length > 0) {
        this._activeProvider = "AIServer (agy)";
        this._activeModel = "agy-engine";
        this._connected = true;

        // Yield in natural word chunks with slight pause for smooth UI rendering
        const words = response.split(/(\s+)/);
        for (const word of words) {
          yield word;
          await new Promise((r) => setTimeout(r, 6));
        }
        return;
      }
    } catch (err) {
      console.warn(`[OmniRouteClient] AIServer stream failed: ${err}`);
    }

    // Secondary fallback: Try OpenAI-compatible streaming
    try {
      const allMessages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [];
      if (systemPrompt) {
        allMessages.push({ role: "system", content: systemPrompt });
      }
      for (const msg of messages) {
        allMessages.push({
          role: msg.role as "system" | "user" | "assistant",
          content: msg.content,
        });
      }
      const [client, defaultModel] = this._getClient();
      const stream = await client.chat.completions.create({
        model: route || defaultModel,
        messages: allMessages,
        temperature,
        max_tokens: maxTokens,
        stream: true,
      });

      this._connected = true;
      for await (const chunk of stream) {
        const content = chunk.choices?.[0]?.delta?.content;
        if (content) {
          yield content;
        }
      }
      return;
    } catch (err) {
      console.warn(`OpenAI-compatible stream failed: ${err}`);
    }

    // Tertiary fallback: direct Gemini streaming
    yield* this._generateGeminiStream(messages, temperature, maxTokens, systemPrompt);
  }

  /**
   * Check connection to AIServer or gateway.
   */
  async checkConnection(): Promise<boolean> {
    const aiServerHealth = await checkAIServerStatus();
    if (aiServerHealth.online) {
      this._connected = true;
      return true;
    }
    return false;
  }

  /**
   * List available models.
   */
  async listModels(): Promise<string[]> {
    return ["agy-engine", "agy-1.4.7"];
  }

  get activeProvider(): string {
    return this._activeProvider;
  }

  get activeModel(): string {
    return this._activeModel;
  }

  get isConnected(): boolean {
    return this._connected;
  }
}

// Singleton
export const omnirouteClient = new OmniRouteClient();
