import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Sparkles, RotateCcw, Copy, Check, Code, Bug, FileSearch, Lightbulb, Mic, MicOff, Volume2, Eye } from 'lucide-react';
import PerceptionWidget from '../components/PerceptionWidget';

/* ═══════════════════════════════════════════════════════════
   CHAT INTERFACE & VOICE ASSISTANT — Clean layout & Wake Word (§15)
   
   Supports:
   - Text chat with SSE streaming
   - Continuous Wake Word Detection ("Hey Markus", "Hello Markus", "Markus", "Hey Mark")
   - Voice Input (Web Speech Recognition API)
   - Text-to-Speech playback (Web Speech Synthesis API)
   ═══════════════════════════════════════════════════════════ */

import { useAIState } from '../context/AIStateContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
}

export default function ChatPage() {
  const { aiState, setAiState } = useAIState();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [wakeWordMode, setWakeWordMode] = useState(false);
  const [showPerception, setShowPerception] = useState(false);
  const [conversationId] = useState(() => crypto.randomUUID());
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  // ── Pre-select a high-quality TTS voice at mount (avoid per-speak delay) ──
  const selectedVoiceRef = useRef<SpeechSynthesisVoice | null>(null);
  useEffect(() => {
    const pickVoice = () => {
      const voices = window.speechSynthesis?.getVoices() || [];
      const currentLang = localStorage.getItem('markus_language') || 'ta-IN';

      if (currentLang === 'ta-IN') {
        const tamil = voices.find(v => 
          v.lang.toLowerCase().replace('_', '-').startsWith('ta') ||
          v.name.toLowerCase().includes('tamil') ||
          v.name.toLowerCase().includes('valluvar') ||
          v.name.toLowerCase().includes('pallavi')
        );
        if (tamil) { selectedVoiceRef.current = tamil; return; }
        const inVoice = voices.find(v => v.lang.toLowerCase().includes('en-in') || v.name.toLowerCase().includes('india'));
        if (inVoice) { selectedVoiceRef.current = inVoice; return; }
      }

      // Prefer high-quality English voices
      const preferred = [
        'Google US English',
        'Microsoft Zira',
        'Microsoft David',
        'Google UK English Male',
        'Samantha',
        'Alex',
      ];
      for (const name of preferred) {
        const v = voices.find(voice => voice.name.includes(name));
        if (v) { selectedVoiceRef.current = v; return; }
      }
      const en = voices.find(v => v.lang.startsWith('en'));
      if (en) { selectedVoiceRef.current = en; return; }

      if (voices.length > 0) selectedVoiceRef.current = voices[0];
    };
    pickVoice();
    window.speechSynthesis?.addEventListener('voiceschanged', pickVoice);
    return () => window.speechSynthesis?.removeEventListener('voiceschanged', pickVoice);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  const wakeWordModeRef = useRef(wakeWordMode);
  const isStartedRef = useRef(false);
  const consecutiveFailsRef = useRef(0);
  const restartTimerRef = useRef<any>(null);
  const lastErrorRef = useRef<string | null>(null);
  const chatSilenceTimerRef = useRef<any>(null);
  const sendMessageWithTextRef = useRef<(text: string) => Promise<void>>(async () => {});

  useEffect(() => {
    wakeWordModeRef.current = wakeWordMode;
  }, [wakeWordMode]);

  // Setup Web Speech Recognition API (single initialization, never re-created)
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = localStorage.getItem('markus_language') || 'ta-IN';

    recognition.onstart = () => {
      isStartedRef.current = true;
      consecutiveFailsRef.current = 0; // Reset on successful start
      lastErrorRef.current = null;
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      consecutiveFailsRef.current = 0; // Got results — reset failures
      let transcript = '';
      let isFinal = false;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
        if (event.results[i].isFinal) isFinal = true;
      }

      const lower = transcript.toLowerCase();

      const wakeWordFound = ['hey markus', 'hello markus', 'hey mark', 'markus', 'hello mark'].some(w => lower.includes(w));

      if (wakeWordFound || !wakeWordModeRef.current) {
        let cleaned = transcript;
        ['hey markus', 'hello markus', 'hey mark', 'markus', 'hello mark'].forEach(w => {
          cleaned = cleaned.replace(new RegExp(w, 'gi'), '').trim();
        });

        const targetText = cleaned || transcript;
        if (targetText) {
          setInput(targetText);
        }

        if (chatSilenceTimerRef.current) clearTimeout(chatSilenceTimerRef.current);

        if (isFinal && targetText.trim()) {
          sendMessageWithTextRef.current(targetText);
        } else if (targetText.trim()) {
          chatSilenceTimerRef.current = setTimeout(() => {
            if (targetText.trim()) {
              sendMessageWithTextRef.current(targetText);
            }
          }, 1200);
        }
      }
    };

    recognition.onerror = (err: any) => {
      const errorType = err.error || '';
      lastErrorRef.current = errorType;

      // These are non-fatal — recognition will fire onend next, we handle restart there
      if (errorType === 'no-speech' || errorType === 'aborted') {
        return; // Silently ignore — no console spam
      }

      // Fatal permission errors — stop everything
      if (errorType === 'not-allowed' || errorType === 'service-not-allowed') {
        console.warn('[Markus] Microphone permission denied');
        wakeWordModeRef.current = false;
        setWakeWordMode(false);
        setIsListening(false);
        isStartedRef.current = false;
        return;
      }

      // Network error: Browser Speech Recognition cloud endpoint unreachable
      if (errorType === 'network') {
        console.warn('[Markus] Web Speech API network error: Browser could not reach cloud speech recognition service.');
        wakeWordModeRef.current = false;
        setWakeWordMode(false);
        setIsListening(false);
        isStartedRef.current = false;
        consecutiveFailsRef.current = 0;
        return;
      }

      console.warn('[Markus] Speech recognition error:', errorType);
    };

    recognition.onend = () => {
      isStartedRef.current = false;

      // If wake word mode was turned off or a fatal/network error happened, just stop
      if (!wakeWordModeRef.current || lastErrorRef.current === 'network' || lastErrorRef.current === 'not-allowed') {
        setIsListening(false);
        return;
      }

      // Track consecutive restarts to detect abort loops
      consecutiveFailsRef.current += 1;
      const fails = consecutiveFailsRef.current;

      // After 5 consecutive failures, give up and disable wake word
      if (fails >= 5) {
        console.warn('[Markus] Too many consecutive speech failures — disabling wake word mode');
        wakeWordModeRef.current = false;
        setWakeWordMode(false);
        setIsListening(false);
        consecutiveFailsRef.current = 0;
        return;
      }

      // Exponential backoff: 500ms, 1s, 2s, 4s (capped)
      const delay = Math.min(500 * Math.pow(2, fails - 1), 10000);

      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);

      restartTimerRef.current = setTimeout(() => {
        restartTimerRef.current = null;
        if (wakeWordModeRef.current && !isStartedRef.current) {
          try {
            recognition.start();
          } catch {
            // Already started or browser blocked — don't loop
          }
        }
      }, delay);
    };

    recognitionRef.current = recognition;

    return () => {
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      recognition.onstart = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      try { recognition.stop(); } catch {}
      isStartedRef.current = false;
    };
  }, []);

  // Toggle voice recognition
  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech Recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
      return;
    }

    if (isListening || isStartedRef.current) {
      // --- STOP ---
      wakeWordModeRef.current = false;
      setWakeWordMode(false);
      if (restartTimerRef.current) {
        clearTimeout(restartTimerRef.current);
        restartTimerRef.current = null;
      }
      try { recognitionRef.current.stop(); } catch {}
      isStartedRef.current = false;
      setIsListening(false);
      setAiState('idle');
      consecutiveFailsRef.current = 0;
    } else {
      // --- START ---
      wakeWordModeRef.current = true;
      setWakeWordMode(true);
      setAiState('listening');
      consecutiveFailsRef.current = 0;
      if (!isStartedRef.current) {
        try {
          recognitionRef.current.start();
        } catch (e: any) {
          if (e.name !== 'InvalidStateError') {
            console.error('[Markus] Failed to start speech recognition:', e);
          }
        }
      }
    }
  };

  // ── Helper: speak text with pre-selected voice ──
  const speakWithVoice = useCallback((text: string, onEnd?: () => void) => {
    if (!window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const currentLang = localStorage.getItem('markus_language') || 'ta-IN';
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = currentLang;
    if (selectedVoiceRef.current) utterance.voice = selectedVoiceRef.current;
    utterance.rate = 1.05;
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();
    window.speechSynthesis.speak(utterance);
  }, []);

  const sendMessageWithText = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsStreaming(true);
    setAiState('thinking');

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      const res = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: trimmed,
          conversation_id: conversationId,
          stream: true,
        }),
      });

      if (!res.ok) throw new Error('Failed to send message');

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let fullContent = '';
        // ── Track sentences for streaming TTS (speak as sentences arrive) ──
        let spokenLength = 0;
        let sentenceCount = 0;
        const MAX_SPEAK_SENTENCES = 3;
        const MAX_SPEAK_CHARS = 500;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value);
          const lines = text.split('\n').filter(l => l.startsWith('data: '));

          for (const line of lines) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.done || data.type === 'done' || data.content === '[DONE]') continue;
              if (data.type === 'metadata' || (typeof data.content === 'string' && data.content.startsWith('{"intent":'))) {
                continue;
              }
              if (data.state) {
                setAiState(data.state);
              }
              if (data.content && data.content !== '[DONE]') {
                fullContent += data.content;
                setMessages(prev => prev.map(m =>
                  m.id === assistantMsg.id ? { ...m, content: fullContent, intent: data.intent } : m
                ));

                // ── Start speaking after each complete sentence (don't wait for full response) ──
                if (window.speechSynthesis && sentenceCount < MAX_SPEAK_SENTENCES && spokenLength < MAX_SPEAK_CHARS) {
                  const unspoken = fullContent.slice(spokenLength);
                  // Find the last sentence boundary in unspoken text
                  const sentenceEnd = unspoken.search(/[.!?]\s/);
                  if (sentenceEnd !== -1) {
                    const sentence = unspoken.slice(0, sentenceEnd + 1)
                      .replace(/```[\s\S]*?```/g, '')
                      .replace(/`([^`]+)`/g, '$1')
                      .replace(/[*#_~`]/g, '')
                      .trim();
                    if (sentence && sentenceCount === 0) setAiState('speaking');
                    if (sentence) {
                      speakWithVoice(sentence);
                      sentenceCount++;
                    }
                    spokenLength += sentenceEnd + 2;
                  }
                }
              }
            } catch { /* ignore parse errors */ }
          }
        }

        // ── Speak any remaining unspoken text (up to cap) ──
        if (window.speechSynthesis && fullContent && sentenceCount === 0) {
          // Nothing was spoken during streaming — speak the first chunk now
          setAiState('speaking');
          const cleanText = fullContent
            .replace(/```[\s\S]*?```/g, 'Code output generated.')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/[*#_~`]/g, '')
            .trim()
            .slice(0, MAX_SPEAK_CHARS);
          speakWithVoice(cleanText, () => {
            setAiState('success');
            setTimeout(() => setAiState('idle'), 500);
          });
        } else {
          setAiState('success');
          setTimeout(() => setAiState('idle'), 500);
        }
      }
    } catch (e) {
      setAiState('error');
      setMessages(prev => prev.map(m =>
        m.id === assistantMsg.id
          ? { ...m, content: 'Unable to reach Markus backend. Make sure the server is running on port 8000.\n\n```\npython markus/main.py\n```' }
          : m
      ));
    }

    setIsStreaming(false);
  };

  sendMessageWithTextRef.current = sendMessageWithText;

  const sendMessage = () => sendMessageWithText(input);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 48px)',
      animation: 'fadeIn 0.5s ease',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
        flexShrink: 0,
      }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 2 }}>Chat & Voice Assistant</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            Say <span style={{ color: 'var(--ai-cyan)', fontWeight: 600 }}>"Hey Markus"</span> or click the microphone to speak
          </p>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Perception / Face Emotion Toggle */}
          <button
            onClick={() => setShowPerception(!showPerception)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 12px',
              borderRadius: 12,
              border: showPerception ? '1px solid var(--ai-purple)' : '1px solid rgba(255,255,255,0.08)',
              background: showPerception ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.04)',
              color: showPerception ? '#A78BFA' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <Eye size={16} />
            {showPerception ? 'Hide Emotion Tracker' : 'Face & Emotion'}
          </button>

          {/* Wake Word Mic Button */}
          <button
            onClick={toggleListening}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              borderRadius: 12,
              border: isListening ? '1px solid var(--ai-cyan)' : '1px solid rgba(255,255,255,0.08)',
              background: isListening ? 'rgba(0,229,255,0.15)' : 'rgba(255,255,255,0.04)',
              color: isListening ? 'var(--ai-cyan)' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: isListening ? '0 0 20px rgba(0,229,255,0.3)' : 'none',
            }}
          >
            {isListening ? <Mic size={16} className="animate-pulse" /> : <MicOff size={16} />}
            {isListening ? 'Listening for "Hey Markus"...' : 'Enable Wake Word'}
          </button>

          <button
            className="btn"
            onClick={() => setMessages([])}
            style={{ gap: 6, fontSize: '0.8rem' }}
          >
            <RotateCcw size={14} /> New Chat
          </button>
        </div>
      </div>

      {/* Main Area with optional Perception Sidebar */}
      <div style={{ display: 'flex', gap: 16, flex: 1, overflow: 'hidden' }}>
        {showPerception && (
          <div style={{ width: 340, flexShrink: 0, overflowY: 'auto' }}>
            <PerceptionWidget />
          </div>
        )}

        {/* Messages Container */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
      <div style={{
        flex: 1,
        overflowY: 'auto',
        paddingRight: 8,
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}>
        {messages.length === 0 && (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            opacity: 0.8,
          }}>
            <Sparkles size={40} color="var(--ai-cyan)" />
            <div style={{ fontSize: '1.1rem', fontWeight: 500 }}>What can I help you build?</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', textAlign: 'center', maxWidth: 420 }}>
              Click <strong>"Enable Wake Word"</strong> above and speak out loud: <br />
              <span style={{ color: 'var(--ai-cyan)' }}>"Hey Markus, explain Clean Architecture"</span>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 500, marginTop: 8 }}>
              {QUICK_PROMPTS.map(p => (
                <button
                  key={p.label}
                  onClick={() => { setInput(p.prompt); inputRef.current?.focus(); }}
                  className="glass-card"
                  style={{
                    padding: '8px 14px',
                    cursor: 'pointer',
                    border: '1px solid rgba(255,255,255,0.06)',
                    fontSize: '0.78rem',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    transition: 'all 0.2s',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: 10,
                  }}
                >
                  <p.icon size={13} style={{ color: p.color }} />
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageItem key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        flexShrink: 0,
        paddingTop: 16,
        borderTop: '1px solid rgba(255,255,255,0.06)',
        marginTop: 8,
      }}>
        <div className="glass-card" style={{
          display: 'flex',
          alignItems: 'flex-end',
          padding: '12px 16px',
          gap: 12,
          borderRadius: 16,
          borderColor: isListening ? 'rgba(0,229,255,0.4)' : undefined,
          boxShadow: isListening ? '0 0 20px rgba(0,229,255,0.15)' : undefined,
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? 'Listening for speech / "Hey Markus"...' : 'Ask Markus anything...'}
            rows={1}
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              fontFamily: 'var(--font-body)',
              resize: 'none',
              minHeight: 24,
              maxHeight: 120,
              lineHeight: 1.5,
            }}
          />

          {/* Microphone button inside input */}
          <button
            onClick={toggleListening}
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              border: 'none',
              background: isListening ? 'rgba(0, 229, 255, 0.2)' : 'rgba(255,255,255,0.06)',
              color: isListening ? 'var(--ai-cyan)' : 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              flexShrink: 0,
            }}
            title={isListening ? 'Disable microphone' : 'Enable microphone wake word'}
          >
            {isListening ? <Mic size={16} className="animate-pulse" /> : <MicOff size={16} />}
          </button>

          <button
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              border: 'none',
              background: input.trim()
                ? 'linear-gradient(135deg, #00E5FF, #3B82F6)'
                : 'rgba(255,255,255,0.06)',
              color: 'white',
              cursor: input.trim() ? 'pointer' : 'default',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              flexShrink: 0,
            }}
          >
            <Send size={16} />
          </button>
        </div>
        <div style={{
          fontSize: '0.65rem',
          color: 'var(--text-disabled)',
          textAlign: 'center',
          marginTop: 8,
        }}>
          Markus routes your message through OmniRoute to the best available AI model
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}

// ── Message Item ──
function MessageItem({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const copyContent = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const speakText = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const currentLang = localStorage.getItem('markus_language') || 'ta-IN';
      const clean = message.content.replace(/```[\s\S]*?```/g, '').replace(/[*#_~`]/g, '');
      const utterance = new SpeechSynthesisUtterance(clean.slice(0, 300));
      utterance.lang = currentLang;
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      animation: 'fadeIn 0.3s ease',
    }}>
      {/* Role label */}
      <div style={{
        fontSize: '0.72rem',
        fontWeight: 600,
        color: isUser ? 'var(--text-muted)' : 'var(--ai-cyan)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}>
        {isUser ? 'You' : '✦ Markus'}
        {message.intent && !isUser && (
          <span style={{
            fontSize: '0.62rem',
            padding: '1px 6px',
            borderRadius: 4,
            background: 'rgba(0,229,255,0.1)',
            color: 'var(--ai-cyan)',
            fontFamily: 'var(--font-code)',
          }}>
            {message.intent}
          </span>
        )}
      </div>

      {/* Content */}
      <div style={{
        fontSize: '0.9rem',
        lineHeight: 1.7,
        color: isUser ? 'var(--text-primary)' : 'var(--text-secondary)',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {message.content || (
          <span style={{
            display: 'inline-flex', gap: 4, alignItems: 'center',
            color: 'var(--text-muted)',
          }}>
            <span className="dot-pulse" style={{
              width: 6, height: 6, borderRadius: '50%',
              background: 'var(--ai-cyan)',
              animation: 'pulse 1s infinite',
            }} />
            Thinking...
          </span>
        )}
      </div>

      {/* Actions */}
      {!isUser && message.content && (
        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
          <button
            onClick={copyContent}
            style={{
              padding: '3px 8px', borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.06)',
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '0.68rem',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              transition: 'all 0.2s',
            }}
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={speakText}
            style={{
              padding: '3px 8px', borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.06)',
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '0.68rem',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              transition: 'all 0.2s',
            }}
          >
            <Volume2 size={11} /> Speak
          </button>
        </div>
      )}
    </div>
  );
}

// Quick prompts
const QUICK_PROMPTS = [
  { label: 'Write code', prompt: 'Write a Python function that ', icon: Code, color: '#FF8A00' },
  { label: 'Debug error', prompt: 'Help me debug this error: ', icon: Bug, color: '#EF4444' },
  { label: 'Research', prompt: 'Research the best approach for ', icon: FileSearch, color: '#6366F1' },
  { label: 'Explain', prompt: 'Explain how ', icon: Lightbulb, color: '#FACC15' },
];
