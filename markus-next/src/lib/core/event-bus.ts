/**
 * Markus AI — Event Bus (§10)
 *
 * Internal pub/sub event bus for agent communication and system-wide notifications.
 * Agents communicate using structured messages through this bus.
 * Direct port from core/event_bus.py.
 */

import { v4 as uuidv4 } from "uuid";

export interface Event {
  id: string;
  type: string;
  source: string;
  target?: string;
  data: unknown;
  timestamp: string;
}

export type EventHandler = (event: Event) => Promise<void>;

class EventBus {
  private _subscribers: Map<string, EventHandler[]> = new Map();
  private _eventHistory: Event[] = [];
  private _maxHistory = 1000;

  constructor() {
    console.log("Event Bus initialized");
  }

  subscribe(eventType: string, handler: EventHandler): void {
    if (!this._subscribers.has(eventType)) {
      this._subscribers.set(eventType, []);
    }
    this._subscribers.get(eventType)!.push(handler);
  }

  unsubscribe(eventType: string, handler: EventHandler): void {
    const handlers = this._subscribers.get(eventType);
    if (handlers) {
      this._subscribers.set(
        eventType,
        handlers.filter((h) => h !== handler),
      );
    }
  }

  async publish(event: Event): Promise<void> {
    this._eventHistory.push(event);
    if (this._eventHistory.length > this._maxHistory) {
      this._eventHistory = this._eventHistory.slice(-this._maxHistory);
    }

    const handlers = this._subscribers.get(event.type) ?? [];
    const wildcardHandlers = this._subscribers.get("*") ?? [];
    const allHandlers = [...handlers, ...wildcardHandlers];

    if (allHandlers.length === 0) {
      return;
    }

    const results = await Promise.allSettled(allHandlers.map((h) => h(event)));
    for (const result of results) {
      if (result.status === "rejected") {
        console.error(`Event handler error for '${event.type}':`, result.reason);
      }
    }
  }

  async emit(eventType: string, source: string, data: unknown = null, target?: string): Promise<void> {
    const event: Event = {
      id: uuidv4().slice(0, 8),
      type: eventType,
      source,
      target,
      data,
      timestamp: new Date().toISOString(),
    };
    await this.publish(event);
  }

  getHistory(eventType?: string, limit: number = 50): Event[] {
    let events = this._eventHistory;
    if (eventType) {
      events = events.filter((e) => e.type === eventType);
    }
    return events.slice(-limit);
  }
}

// Singleton
export const eventBus = new EventBus();
