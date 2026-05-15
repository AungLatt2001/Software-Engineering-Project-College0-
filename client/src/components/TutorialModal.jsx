import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const STEPS = [
  {
    icon: '🎓',
    title: 'Welcome to College0!',
    body: (
      <div>
        <p>College0 is your all-in-one academic portal — from enrolling in courses and tracking grades to submitting reviews and applying for graduation.</p>
        <p style={{ marginTop: 12 }}>This quick 7-step tour walks you through every part of your student experience. You can always ask the AI Assistant if you have questions later.</p>
      </div>
    ),
  },
  {
    icon: '📊',
    title: 'Your Dashboard',
    body: (
      <div>
        <p>The <strong>Dashboard</strong> is your home base. At a glance you'll see:</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <li><strong>Cumulative &amp; Semester GPA</strong> — keep both above 2.0 to stay in good standing</li>
          <li><strong>Warnings</strong> — 3 warnings results in automatic suspension</li>
          <li><strong>Honors</strong> — earned each semester your GPA reaches 3.5 or above</li>
          <li><strong>Outstanding fines</strong> — must be cleared before enrolling or graduating</li>
        </ul>
      </div>
    ),
  },
  {
    icon: '📚',
    title: 'My Courses — Enrolling &amp; Dropping',
    body: (
      <div>
        <p>Go to <strong>My Courses</strong> to browse available sections and manage your schedule.</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <li>Enrollment is only open during the <strong>Registration</strong> phase</li>
          <li>If a section is full you can join the <strong>waitlist</strong> — you'll be auto-enrolled when a seat opens</li>
          <li>Dropping a course during the Running phase earns a <strong>warning</strong></li>
          <li>If your section is cancelled due to low enrollment, you get <strong>special re-registration</strong> rights</li>
        </ul>
      </div>
    ),
  },
  {
    icon: '📋',
    title: 'Your Transcript',
    body: (
      <div>
        <p>The <strong>Transcript</strong> page shows your complete grade history broken down by semester.</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <li>Grades are posted by your instructor during the <strong>Grading</strong> phase</li>
          <li>Each course shows its letter grade and grade points</li>
          <li>Cumulative and semester GPAs are calculated automatically</li>
          <li>You must be enrolled in at least <strong>2 courses per semester</strong> to avoid a warning</li>
        </ul>
      </div>
    ),
  },
  {
    icon: '⭐',
    title: 'Reviews, Complaints &amp; Graduation',
    body: (
      <div>
        <p>The <strong>Reviews &amp; More</strong> page has three tabs:</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <li><strong>Reviews</strong> — rate your courses 1–5 stars during the Grading phase</li>
          <li><strong>Graduation</strong> — apply once you meet the requirements: GPA ≥ 2.0, 0 active warnings, no fines, and enough credits</li>
          <li><strong>Complaints</strong> — file a complaint against any user; the Registrar will review and take action</li>
        </ul>
      </div>
    ),
  },
  {
    icon: '🤖',
    title: 'AI Assistant',
    body: (
      <div>
        <p>The <strong>AI Assistant</strong> can answer any question about College0 — policies, semester phases, enrollment rules, graduation, and more.</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <li>Answers sourced from the <strong>College0 knowledge base</strong> are marked with a green ✓</li>
          <li>If no local answer is found, the question goes to a <strong>general AI</strong> — those responses carry a red hallucination warning so you know to verify with the Registrar</li>
          <li>Use the quick-prompt chips for common questions or type anything you like</li>
        </ul>
      </div>
    ),
  },
  {
    icon: '⚠️',
    title: 'Warnings &amp; Academic Standing',
    body: (
      <div>
        <p>Keep an eye on your academic standing — warnings accumulate and can lead to suspension.</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <li><strong>3 warnings</strong> → account suspended</li>
          <li>Warnings can come from low GPA, dropping courses during Running phase, being under-enrolled, or complaints</li>
          <li>Outstanding <strong>fines</strong> block enrollment and graduation applications</li>
          <li>A <strong>GPA ≥ 3.5</strong> earns an honors distinction each semester</li>
        </ul>
        <div style={{
          marginTop: 18, padding: '12px 16px', background: '#f0fdf4',
          border: '1px solid #86efac', borderRadius: 10,
          fontSize: '0.83rem', color: '#166534', lineHeight: 1.5
        }}>
          ✓ You're all set! Explore your portal and reach out to the AI Assistant any time you need help.
        </div>
      </div>
    ),
  },
];

export default function TutorialModal({ onDismiss }) {
  const [step, setStep] = useState(0);
  const nav = useNavigate();

  const dismiss = async (goTo) => {
    try { await api.post('/tutorial/dismiss'); } catch {}
    onDismiss();
    if (goTo) nav(goTo);
  };

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="modal-overlay open" style={{ zIndex: 2000 }}>
      <div className="tutorial-modal" style={{ position: 'relative' }}>

        <button
          onClick={() => dismiss(null)}
          title="Skip tutorial"
          style={{
            position: 'absolute', top: 14, right: 18,
            background: 'none', border: 'none', fontSize: '1.4rem',
            cursor: 'pointer', color: 'var(--muted)', lineHeight: 1
          }}
        >×</button>

        <div className="tutorial-icon">{current.icon}</div>
        <div className="tutorial-step-count">Step {step + 1} of {STEPS.length}</div>
        <h2 className="tutorial-title">{current.title}</h2>
        <div className="tutorial-body" style={{ textAlign: 'left' }}>{current.body}</div>

        <div className="tutorial-dots">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`tutorial-dot${i === step ? ' active' : ''}`}
              onClick={() => setStep(i)}
            />
          ))}
        </div>

        <div className="tutorial-actions">
          {step > 0 && (
            <button className="btn-secondary" onClick={() => setStep(s => s - 1)}>← Back</button>
          )}
          {isLast ? (
            <button className="btn-primary" onClick={() => dismiss('/dashboard')}>
              Go to Dashboard →
            </button>
          ) : (
            <button className="btn-primary" onClick={() => setStep(s => s + 1)}>
              Next →
            </button>
          )}
          {step === 0 && (
            <button
              onClick={() => dismiss(null)}
              style={{
                background: 'none', border: 'none', fontSize: '0.8rem',
                color: 'var(--muted)', cursor: 'pointer', textDecoration: 'underline'
              }}
            >
              Skip tour
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
