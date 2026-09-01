import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';

export type AIState =
  | 'idle' | 'listening' | 'thinking' | 'planning' | 'coding'
  | 'research' | 'executing' | 'waiting_for_confirmation'
  | 'speaking' | 'success' | 'warning' | 'error';

interface AIStateContextType {
  aiState: AIState;
  setAiState: (state: AIState) => void;
  isConnected: boolean;
}

const AIStateContext = createContext<AIStateContextType>({
  aiState: 'idle',
  setAiState: () => {},
  isConnected: false,
});

const WS_URL = 'ws://localhost:8000/ws';
const MAX_RECONNECT_DELAY = 15000;

export const AIStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [aiState, setAiStateLocal] = useState<AIState>('idle');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectAttempt = 0;

    function connect() {
      if (cancelled) return;

      try {
        ws = new WebSocket(WS_URL);
      } catch {
        scheduleReconnect();
        return;
      }

      const currentWs = ws;

      currentWs.onopen = () => {
        if (cancelled) {
          currentWs.close();
          return;
        }
        reconnectAttempt = 0;
        wsRef.current = currentWs;
        setIsConnected(true);
      };

      currentWs.onmessage = (event) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_change' && data.state) {
            setAiStateLocal(data.state as AIState);
          }
        } catch { /* ignore non-json */ }
      };

      currentWs.onclose = () => {
        if (cancelled) return;
        wsRef.current = null;
        ws = null;
        setIsConnected(false);
        scheduleReconnect();
      };

      currentWs.onerror = () => {
        // onclose fires next — nothing to do here
      };
    }

    function scheduleReconnect() {
      if (cancelled) return;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), MAX_RECONNECT_DELAY);
      reconnectAttempt++;
      reconnectTimer = setTimeout(connect, delay);
    }

    function cleanup() {
      cancelled = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
        ws = null;
      }
      wsRef.current = null;
    }

    // Defer connection to the next microtask so React StrictMode's
    // first-mount cleanup runs BEFORE any WebSocket is ever created.
    // This completely avoids the "closed before established" warning.
    const initTimer = setTimeout(connect, 0);

    return () => {
      clearTimeout(initTimer);
      cleanup();
    };
  }, []);

  const setAiState = useCallback((state: AIState) => {
    setAiStateLocal(state);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'set_state', state }));
    }
  }, []);

  return (
    <AIStateContext.Provider value={{ aiState, setAiState, isConnected }}>
      {children}
    </AIStateContext.Provider>
  );
};

export const useAIState = () => useContext(AIStateContext);
