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

const getWsUrl = (): string | null => {
  if (typeof window === 'undefined') return null;
  // If an explicit WebSocket endpoint is configured in env, use it.
  // Otherwise Markus Next.js backend operates via HTTP REST & SSE (/api/chat/) and does not host raw WS.
  const customWs = (import.meta as any).env?.VITE_WS_URL;
  if (customWs) return customWs;
  return null;
};
const WS_URL = getWsUrl();
const MAX_RECONNECT_DELAY = 15000;

export const AIStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [aiState, setAiStateLocal] = useState<AIState>('idle');
  const [isConnected, setIsConnected] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!WS_URL) {
      // Backend operates over HTTP REST & Server-Sent Events (Next.js App Router).
      // AIState is managed locally in React with full real-time UI/Voice synchronization.
      setIsConnected(true);
      return;
    }

    let cancelled = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectAttempt = 0;

    function connect() {
      if (cancelled || !WS_URL) return;

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
      reconnectAttempt++;
      // If the endpoint does not support WebSockets (handshake timed out), do not spam connection loops
      if (reconnectAttempt >= 2) {
        // Quietly check again on a long interval (e.g. 2 minutes) without flooding console
        reconnectTimer = setTimeout(() => {
          reconnectAttempt = 0;
          connect();
        }, 120000);
        return;
      }
      const delay = Math.min(5000 * Math.pow(2, reconnectAttempt), 30000);
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
      window.removeEventListener('pagehide', onPageHide);
      window.removeEventListener('pageshow', onPageShow);
    }

    // Support Back/Forward Cache (bfcache) by closing active socket during pagehide
    // and reconnecting on pageshow when persisted === true
    function onPageHide() {
      if (ws) {
        try { ws.close(); } catch {}
      }
      if (reconnectTimer) clearTimeout(reconnectTimer);
    }

    function onPageShow(e: PageTransitionEvent) {
      if (e.persisted && !cancelled) {
        connect();
      }
    }

    window.addEventListener('pagehide', onPageHide);
    window.addEventListener('pageshow', onPageShow);

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
