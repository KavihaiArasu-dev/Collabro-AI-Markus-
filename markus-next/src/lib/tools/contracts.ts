/**
 * Markus AI — Tool Contracts & Execution Result Models
 * Direct port from tools/contracts.py.
 */

export interface PreCondition {
  name: string;
  checkFn: (...args: unknown[]) => boolean;
  failureMessage: string;
}

export interface PostCondition {
  assertionType: string;
  targetParam: string;
  timeout: number;
}

export interface ExecutionResult {
  success: boolean;
  verified: boolean;
  data: unknown;
  verificationDetails: unknown;
  executionTimeMs: number;
  error: string | null;
  outputMessage: string;
}

export function createExecutionResult(opts: Partial<ExecutionResult> = {}): ExecutionResult {
  return {
    success: opts.success ?? false,
    verified: opts.verified ?? false,
    data: opts.data ?? null,
    verificationDetails: opts.verificationDetails ?? null,
    executionTimeMs: opts.executionTimeMs ?? 0,
    error: opts.error ?? null,
    outputMessage: opts.outputMessage ?? "",
  };
}

export function executionResultToDict(result: ExecutionResult): Record<string, unknown> {
  return {
    success: result.success,
    verified: result.verified,
    data: result.data,
    verification_details: result.verificationDetails,
    execution_time_ms: Math.round(result.executionTimeMs * 100) / 100,
    error: result.error,
    output_message: result.outputMessage,
  };
}
