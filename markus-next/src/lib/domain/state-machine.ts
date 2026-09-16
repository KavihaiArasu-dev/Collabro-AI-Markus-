/**
 * Markus AI — Conversation & Assistant State Machine (§2, §3)
 * Direct port from domain/state_machine.py.
 */

export enum ConversationState {
  IDLE = "idle",
  ACTIVATED = "activated",
  LISTENING = "listening",
  THINKING = "thinking",
  SPEAKING = "speaking",
  ERROR = "error",
}

export class InvalidTransitionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidTransitionError";
  }
}

const VALID_TRANSITIONS: Record<ConversationState, Set<ConversationState>> = {
  [ConversationState.IDLE]: new Set([ConversationState.ACTIVATED, ConversationState.LISTENING, ConversationState.ERROR]),
  [ConversationState.ACTIVATED]: new Set([ConversationState.LISTENING, ConversationState.IDLE, ConversationState.ERROR]),
  [ConversationState.LISTENING]: new Set([ConversationState.THINKING, ConversationState.IDLE, ConversationState.ERROR]),
  [ConversationState.THINKING]: new Set([ConversationState.SPEAKING, ConversationState.IDLE, ConversationState.ERROR]),
  [ConversationState.SPEAKING]: new Set([ConversationState.IDLE, ConversationState.LISTENING, ConversationState.ERROR]),
  [ConversationState.ERROR]: new Set([ConversationState.IDLE]),
};

export class StateMachine {
  private _currentState: ConversationState;

  constructor(initialState: ConversationState = ConversationState.IDLE) {
    this._currentState = initialState;
  }

  get currentState(): ConversationState {
    return this._currentState;
  }

  transitionTo(newState: ConversationState): ConversationState {
    if (newState === this._currentState) {
      return this._currentState;
    }

    const allowed = VALID_TRANSITIONS[this._currentState] ?? new Set();
    if (!allowed.has(newState)) {
      const validStates = Array.from(allowed).map((s) => s);
      const errMsg = `Cannot transition from ${this._currentState} to ${newState}. Valid: ${JSON.stringify(validStates)}`;
      console.warn(errMsg);
      throw new InvalidTransitionError(errMsg);
    }

    console.debug(`State transition: ${this._currentState} -> ${newState}`);
    this._currentState = newState;
    return this._currentState;
  }
}
