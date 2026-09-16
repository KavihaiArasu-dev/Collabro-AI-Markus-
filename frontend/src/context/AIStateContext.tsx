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

const getWsUrl = () => {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8010/ws';
  // If running locally in dev mode, connect directly to backend (port 8010)
  // regardless of which dev port Vite assigned (5173, 5174, etc.)
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'ws://127.0.0.1:8010/ws';
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws`;
};
const WS_URL = getWsUrl();
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
      // Gentle exponential backoff: 5s, 10s, 20s, then 30s probe when backend is offline
      const delay = reconnectAttempt >= 3 ? 30000 : Math.min(5000 * Math.pow(2, reconnectAttempt), 30000);
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
