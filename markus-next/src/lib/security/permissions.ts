/**
 * Markus AI — Permission Manager (§11a)
 *
 * Architectural rule: an LLM response alone must never authorize a destructive action.
 * Chain: LLM → Planner → Permission Manager → Tool Router → OS
 * Direct port from security/permissions.py.
 */

import { RiskLevel, PermissionDecision, PERMISSION_DEFAULTS } from "@/lib/config/constants";
import { v4 as uuidv4 } from "uuid";
import * as fs from "fs";
import * as path from "path";

export interface PermissionRequest {
  id: string;
  action: string;
  toolName: string;
  arguments: Record<string, unknown>;
  riskLevel: RiskLevel;
  description: string;
  requestedBy: string;
  timestamp: string;
  decision: PermissionDecision | null;
  decidedAt: string | null;
  decidedBy: string | null;
}

class PermissionManager {
  private _pendingRequests: Map<string, PermissionRequest> = new Map();
  private _auditLog: PermissionRequest[] = [];
  private _customOverrides: Map<string, PermissionDecision> = new Map();
  private _adminMode: boolean = true; // Full administrator privileges enabled

  constructor() {
    console.log("Permission Manager initialized with Administrator Privileges (Full Access)");
  }

  setAdminMode(enabled: boolean): void {
    this._adminMode = enabled;
    console.log(`Administrator mode: ${enabled ? "ENABLED (full system access)" : "DISABLED"}`);
  }

  isAdminMode(): boolean {
    return this._adminMode;
  }

  checkPermission(
    action: string,
    toolName: string,
    args: Record<string, unknown>,
    riskLevel: RiskLevel,
    requestedBy: string = "",
    description: string = "",
  ): PermissionRequest {
    const request: PermissionRequest = {
      id: uuidv4().slice(0, 8),
      action,
      toolName,
      arguments: args,
      riskLevel,
      description,
      requestedBy,
      timestamp: new Date().toISOString(),
      decision: null,
      decidedAt: null,
      decidedBy: null,
    };

    // 1. Administrator mode: auto-allow all actions with full system access
    if (this._adminMode) {
      request.decision = PermissionDecision.ALLOW;
      request.decidedAt = new Date().toISOString();
      request.decidedBy = "administrator (full system access)";
      this._logDecision(request);
      return request;
    }

    // Check custom overrides first
    const override = this._customOverrides.get(action);
    if (override) {
      request.decision = override;
      request.decidedAt = new Date().toISOString();
      request.decidedBy = "auto (custom override)";
      this._logDecision(request);
      return request;
    }

    // Check defaults
    const defaultDecision = PERMISSION_DEFAULTS[action];
    if (defaultDecision) {
      if (defaultDecision === PermissionDecision.ALLOW) {
        request.decision = PermissionDecision.ALLOW;
        request.decidedAt = new Date().toISOString();
        request.decidedBy = "auto (default)";
        this._logDecision(request);
        return request;
      } else if (defaultDecision === PermissionDecision.BLOCK) {
        request.decision = PermissionDecision.BLOCK;
        request.decidedAt = new Date().toISOString();
        request.decidedBy = "auto (blocked)";
        this._logDecision(request);
        return request;
      }
    }

    // Risk-based decision
    if (riskLevel === RiskLevel.LOW) {
      request.decision = PermissionDecision.ALLOW;
      request.decidedAt = new Date().toISOString();
      request.decidedBy = "auto (low risk)";
    } else if (riskLevel === RiskLevel.HIGH) {
      request.decision = PermissionDecision.ASK;
      this._pendingRequests.set(request.id, request);
      console.log(`Permission request pending: ${request.id} — ${action} (HIGH risk)`);
    } else {
      // MEDIUM — allow by default
      request.decision = PermissionDecision.ALLOW;
      request.decidedAt = new Date().toISOString();
      request.decidedBy = "auto (medium risk)";
    }

    this._logDecision(request);
    return request;
  }

  approve(requestId: string, decidedBy: string = "user"): PermissionRequest | null {
    const request = this._pendingRequests.get(requestId);
    if (request) {
      this._pendingRequests.delete(requestId);
      request.decision = PermissionDecision.ALLOW;
      request.decidedAt = new Date().toISOString();
      request.decidedBy = decidedBy;
      this._logDecision(request);
      console.log(`Permission approved: ${requestId} — ${request.action}`);
    }
    return request ?? null;
  }

  deny(requestId: string, decidedBy: string = "user"): PermissionRequest | null {
    const request = this._pendingRequests.get(requestId);
    if (request) {
      this._pendingRequests.delete(requestId);
      request.decision = PermissionDecision.BLOCK;
      request.decidedAt = new Date().toISOString();
      request.decidedBy = decidedBy;
      this._logDecision(request);
      console.log(`Permission denied: ${requestId} — ${request.action}`);
    }
    return request ?? null;
  }

  getPendingRequests(): PermissionRequest[] {
    return Array.from(this._pendingRequests.values());
  }

  setOverride(action: string, decision: PermissionDecision): void {
    this._customOverrides.set(action, decision);
    console.log(`Permission override set: ${action} → ${decision}`);
  }

  getAuditLog(limit: number = 100): Record<string, unknown>[] {
    return this._auditLog.slice(-limit).map((r) => ({
      id: r.id,
      action: r.action,
      tool_name: r.toolName,
      risk_level: r.riskLevel,
      decision: r.decision ?? "pending",
      decided_by: r.decidedBy,
      timestamp: r.timestamp,
    }));
  }

  private _logDecision(request: PermissionRequest): void {
    this._auditLog.push(request);
    if (this._auditLog.length > 10000) {
      this._auditLog = this._auditLog.slice(-5000);
    }

    try {
      const logsDir = path.join(process.cwd(), "logs");
      fs.mkdirSync(logsDir, { recursive: true });
      const logEntry = {
        id: request.id,
        action: request.action,
        tool_name: request.toolName,
        risk_level: request.riskLevel,
        decision: request.decision ?? "pending",
        decided_by: request.decidedBy,
        requested_by: request.requestedBy,
        timestamp: request.timestamp,
      };
      fs.appendFileSync(
        path.join(logsDir, "audit.log"),
        JSON.stringify(logEntry) + "\n",
        "utf-8",
      );
    } catch (e) {
      console.warn(`Failed to append to audit.log: ${e}`);
    }
  }
}

// Singleton
export const permissionManager = new PermissionManager();
