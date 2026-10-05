/**
 * Markus AI — System Permissions API Route
 */

import { NextRequest, NextResponse } from "next/server";
import { permissionManager } from "@/lib/security/permissions";

export async function GET() {
  return NextResponse.json({
    admin_mode: permissionManager.isAdminMode(),
    pending: permissionManager.getPendingRequests().map((r) => ({
      id: r.id,
      action: r.action,
      risk_level: r.riskLevel,
      description: r.description,
      requested_by: r.requestedBy,
      timestamp: r.timestamp,
    })),
    audit_log: permissionManager.getAuditLog(50),
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { request_id, action: decisionAction, admin_mode } = body;

  if (typeof admin_mode === "boolean") {
    permissionManager.setAdminMode(admin_mode);
    return NextResponse.json({ status: "success", admin_mode: permissionManager.isAdminMode() });
  }

  if (!request_id) {
    return NextResponse.json({ error: "request_id is required" }, { status: 400 });
  }

  let result;
  if (decisionAction === "approve") {
    result = permissionManager.approve(request_id);
  } else if (decisionAction === "deny") {
    result = permissionManager.deny(request_id);
  } else {
    return NextResponse.json({ error: "action must be 'approve' or 'deny'" }, { status: 400 });
  }

  if (result) {
    return NextResponse.json({ status: decisionAction === "approve" ? "approved" : "denied", action: result.action });
  }
  return NextResponse.json({ error: "Request not found" }, { status: 404 });
}
