import { execFile } from 'child_process';

const AISERVER_URL = process.env.AISERVER_URL || 'http://localhost:3001';

export interface AIServerOptions {
  continueSession?: boolean;
  timeoutMs?: number;
}

export interface AIServerResponse {
  success: boolean;
  result?: string;
  error?: string;
  durationMs?: number;
}

/**
 * Fallback to direct local agy execution if the HTTP AIServer is unreachable.
 */
function runAgyDirectly(prompt: string, options?: AIServerOptions): Promise<string> {
  return new Promise((resolve, reject) => {
    const args: string[] = [];
    if (options?.continueSession) {
      args.push('-c');
    }
    args.push('-p', prompt);
    args.push('--dangerously-skip-permissions');

    const timeoutMs = options?.timeoutMs || 180000;

    execFile(
      'agy',
      args,
      {
        windowsHide: true,
        maxBuffer: 50 * 1024 * 1024,
        timeout: timeoutMs,
      },
      (error, stdout, stderr) => {
        if (error) {
          return reject(new Error(error.message || stderr || 'Local agy execution failed.'));
        }
        resolve(stdout ? stdout.trim() : '');
      }
    );
  });
}

/**
 * Queries the AIServer HTTP service at http://localhost:3001/api/query,
 * falling back to direct local agy process if the server is offline.
 */
export async function queryAIServer(
  prompt: string,
  options?: AIServerOptions
): Promise<string> {
  const timeoutMs = options?.timeoutMs || 180000;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const res = await fetch(`${AISERVER_URL}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: prompt,
        continueSession: options?.continueSession ?? false,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`AIServer returned HTTP ${res.status}: ${res.statusText}`);
    }

    const data: AIServerResponse = await res.json();
    if (!data.success || data.error) {
      throw new Error(data.error || 'AIServer failed to execute query.');
    }

    return data.result ?? '';
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.warn(`[AIServerClient] HTTP request failed (${message}). Falling back to direct agy execution...`);
    return runAgyDirectly(prompt, options);
  }
}

/**
 * Checks if the AIServer is running and healthy.
 */
export async function checkAIServerStatus(): Promise<{ online: boolean; details?: Record<string, unknown> }> {
  try {
    const res = await fetch(`${AISERVER_URL}/api/status`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const data = await res.json();
      return { online: true, details: data };
    }
  } catch {
    // server not responding
  }
  return { online: false };
}
