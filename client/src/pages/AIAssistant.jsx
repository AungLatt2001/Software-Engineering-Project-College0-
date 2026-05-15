import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../App';
import api from '../api';

const QUICK = [
  'What are the graduation requirements?',
  'How does the warning system work?',
  'What are the semester phases?',
  'How do course reviews work?',
  'How do I enroll in courses?',
  'What happens when a course is cancelled?',
  'How do instructor complaints work?',
  'What is the waitlist policy?',
];

const BotIcon = () => (
  <div style={{
    width: 32, height: 32, borderRadius: '50%', background: 'var(--navy)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, fontSize: '0.85rem', color: '#fff', fontWeight: 700
  }}>
    🎓
  </div>
);

const UserIcon = () => (
  <div style={{
    width: 32, height: 32, borderRadius: '50%', background: '#e2e8f0',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, fontSize: '0.9rem'
  }}>
    👤
  </div>
);

function Message({ msg }) {
  const isUser = msg.role === 'user';

  if (isUser) {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'flex-end', gap: 10, marginBottom: 18 }}>
        <div style={{
          background: 'var(--navy)', color: '#fff', borderRadius: '18px 18px 4px 18px',
          padding: '10px 16px', maxWidth: '68%', fontSize: '0.88rem', lineHeight: 1.55,
          wordBreak: 'break-word'
        }}>
          {msg.text}
        </div>
        <UserIcon />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}>
      <BotIcon />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          background: '#f1f5f9', borderRadius: '18px 18px 18px 4px',
          padding: '10px 16px', fontSize: '0.88rem', lineHeight: 1.6,
          color: 'var(--text)', wordBreak: 'break-word', whiteSpace: 'pre-wrap'
        }}>
          {msg.text}
        </div>
        {msg.source === 'llm' && (
          <div style={{
            marginTop: 7, padding: '8px 12px', background: '#fffbeb',
            border: '1px solid #fcd34d', borderRadius: 8,
            fontSize: '0.74rem', color: '#92400e', lineHeight: 1.5,
            display: 'flex', gap: 7, alignItems: 'flex-start'
          }}>
            <span style={{ flexShrink: 0 }}>⚠</span>
            <span>
              No matching information was found in College0's local knowledge store, so this answer
              comes from the general LLM. It may be inaccurate or hallucinated — verify important
              details with the registrar.
            </span>
          </div>
        )}
        {msg.source === 'local' && (
          <div style={{ marginTop: 6, fontSize: '0.7rem', color: '#16a34a', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
            <span>✓</span> From College0 knowledge base
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}>
      <BotIcon />
      <div style={{
        background: '#f1f5f9', borderRadius: '18px 18px 18px 4px',
        padding: '12px 18px', display: 'flex', gap: 5, alignItems: 'center'
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: '50%', background: '#94a3b8',
            animation: 'chatBounce 1.2s infinite',
            animationDelay: `${i * 0.2}s`
          }} />
        ))}
      </div>
    </div>
  );
}

export default function AIAssistant() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: 'Hi! I\'m the College0 Assistant. Ask me anything about policies, grades, enrollment, semester phases, graduation, and more.',
      source: 'local',
    }
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const send = async (text) => {
    const q = (text || input).trim();
    if (!q || busy) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    setBusy(true);
    try {
      const r = await api.post('/ai', { question: q });
      setMessages(prev => [...prev, { role: 'bot', text: r.data.answer, source: r.data.source || 'local' }]);
    } catch {
      setMessages(prev => [...prev, { role: 'bot', text: 'Sorry, something went wrong. Please try again.', source: 'local' }]);
    } finally {
      setBusy(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const newChat = () => {
    setMessages([{
      role: 'bot',
      text: 'Hi! I\'m the College0 Assistant. Ask me anything about policies, grades, enrollment, semester phases, graduation, and more.',
      source: 'local',
    }]);
    setInput('');
    inputRef.current?.focus();
  };

  const hasOnlyGreeting = messages.length === 1;

  return (
    <div className="chat-shell">
      {/* Header */}
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 9, background: 'var(--navy)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem'
          }}>🎓</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--navy)' }}>College0 Assistant</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>Powered by the College0 knowledge base</div>
          </div>
        </div>
        <button className="chat-new-btn" onClick={newChat}>New chat</button>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((m, i) => <Message key={i} msg={m} />)}
        {busy && <TypingIndicator />}

        {/* Quick prompts shown only on fresh chat */}
        {hasOnlyGreeting && !busy && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', fontWeight: 600, marginBottom: 10, textAlign: 'center' }}>
              Try asking…
            </div>
            <div className="chat-quick-grid">
              {QUICK.map(q => (
                <button key={q} className="chat-quick-chip" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-bar">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Ask a question…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          disabled={busy}
        />
        <button
          className="chat-send-btn"
          onClick={() => send()}
          disabled={busy || !input.trim()}
          title="Send (Enter)"
        >
          ➤
        </button>
      </div>
    </div>
  );
}
