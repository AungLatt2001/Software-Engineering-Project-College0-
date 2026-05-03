import React, { useState } from 'react';
import api from '../api';

const QUICK = [
  'What are the graduation requirements?',
  'How does the warning system work?',
  'What are the semester phases?',
  'How do course reviews work?',
  'What is my current GPA?',
  'How does the waitlist work?',
];

export default function AIAssistant() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);

  const ask = async (q) => {
    if (!q.trim()) return;
    setBusy(true); setAnswer('');
    try {
      const r = await api.post('/ai', { question: q });
      setAnswer(r.data.answer);
      setQuestion(q);
    } catch { setAnswer('Sorry, something went wrong.'); }
    finally { setBusy(false); }
  };

  return (
    <>
      <div className="page-header">
        <h1>AI Assistant</h1>
        <p>Ask questions about College0 — answered from local knowledge.</p>
      </div>

      <div className="ai-card">
        <form onSubmit={e => { e.preventDefault(); ask(question); }}>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>Your Question</label>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="e.g. What are the graduation requirements?"
              style={{ minHeight: 90 }}
            />
          </div>
          <div className="ai-btn-row">
            <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Thinking…' : 'Ask AI'}</button>
            <button type="button" className="btn-secondary" onClick={() => { setQuestion(''); setAnswer(''); }}>Clear</button>
          </div>
        </form>

        {answer && (
          <div className="ai-answer">
            <strong style={{ display: 'block', marginBottom: 6, fontSize: '0.78rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Answer</strong>
            {answer}
          </div>
        )}

        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--muted)', marginBottom: 10 }}>Quick Questions:</div>
          <div className="quick-questions">
            {QUICK.map(q => (
              <button key={q} className="quick-btn" onClick={() => ask(q)}>{q}</button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
