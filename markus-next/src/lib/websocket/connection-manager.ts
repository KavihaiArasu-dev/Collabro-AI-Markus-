/**
 * Markus AI — WebSocket Connection Manager
 *
 * Manages WebSocket connections for real-time state broadcasting.
 * Port from application/websocket.py.
 */

import { AIState, WSEventType } from "@/lib/config/constants";

export interface WSConnection {
  id: string;
  send: (data: string) => void;
  close: () => void;
}

class ConnectionManager {
  private _connections: Map<string, WSConnection> = new Map();
  private _currentState: AIState = AIState.IDLE;

  constructor() {
    console.log("WebSocket ConnectionManager initialized");
  }

  addConnection(conn: WSConnection): void {
    this._connections.set(conn.id, conn);
    console.log(`WS client connected: ${conn.id} (total: ${this._connections.size})`);

    // Send current state to new connection
    this._sendTo(conn.id, {
      type: WSEventType.STATE_CHANGE,
      data: { state: this._currentState },
    });
  }

  removeConnection(connId: string): void {
    this._connections.delete(connId);
    console.log(`WS client disconnected: ${connId} (total: ${this._connections.size})`);
  }

  async broadcastState(state: AIState, extra?: Record<string, unknown>): Promise<void> {
    this._currentState = state;
    await this._broadcast({
      type: WSEventType.STATE_CHANGE,
      data: { state, ...extra },
    });
  }

  async broadcast(type: WSEventType, data: Record<string, unknown>): Promise<void> {
    await this._broadcast({ type, data });
  }

  get currentState(): AIState {
    return this._currentState;
  }

  get connectionCount(): number {
    return this._connections.size;
  }

  private async _broadcast(message: Record<string, unknown>): Promise<void> {
    const payload = JSON.stringify(message);
    for (const [id, conn] of this._connections) {
      try {
        conn.send(payload);
      } catch (e) {
        console.warn(`Failed to send to ${id}: ${e}`);
        this._connections.delete(id);
      }
    }
  }

  private _sendTo(connId: string, message: Record<string, unknown>): void {
    const conn = this._connections.get(connId);
    if (conn) {
      try {
        conn.send(JSON.stringify(message));
      } catch (e) {
        console.warn(`Failed to send to ${connId}: ${e}`);
      }
    }
  }
}

// Singleton
export const connectionManager = new ConnectionManager();
