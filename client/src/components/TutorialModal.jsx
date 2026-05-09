import React, { useState } from 'react';
import api from '../api';

const STEPS = [
  {
    icon: '📚',
    title: 'Welcome to College0!',
    body: 'This is your academic portal — your one-stop hub for managing courses, grades, and academic records. Let\'s walk you through the key features.',
  },
  {
    icon: '⎇',
    title: 'Your Dashboard',
    body: 'Your Dashboard shows your GPA, warning count, honor count, and enrolled courses at a glance. Check it regularly to stay on top of your academic standing.',
  },
  {
    icon: '📚',
    title: 'My Courses',
    body: 'During the Registration phase, go to My Courses to enroll in or drop sections. You can join the waitlist if a section is full — you\'ll be auto-enrolled when a seat opens.',
  },
  {
    icon: '📋',
    title: 'Transcript',
    body: 'Your Transcript shows your full grade history, cumulative GPA, and semester GPA across all completed courses.',
  },
  {
    icon: '⭐',
    title: 'Reviews, Graduation & Complaints',
    body: 'During the Grading phase, submit anonymous course reviews. You can also apply for graduation here (once you meet requirements), or file a complaint if needed.',
  },
  {
    icon: '⚠️',
    title: 'Important Rules',
    body: 'You must be enrolled in at least 2 courses per semester to avoid a warning. 3 warnings = suspension. Courses with fewer than 3 students will be cancelled — you\'ll get a special re-registration period if that happens.',
  },
  {
    icon: '🤖',
    title: 'AI Assistant',
    body: 'Have questions? The AI Assistant (available in the sidebar) can answer questions about graduation requirements, GPA, phases, warnings, and more.',
  },
];

export default function TutorialModal({ onDismiss }) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const handleDismiss = async () => {
    try { await api.post('/tutorial/dismiss'); } catch {}
    onDismiss();
  };

  return (
    <div className="modal-overlay">
      <div className="tutorial-modal">
        <div className="tutorial-icon">{current.icon}</div>
        <div className="tutorial-step-count">{step + 1} of {STEPS.length}</div>
        <h2 className="tutorial-title">{current.title}</h2>
        <p className="tutorial-body">{current.body}</p>

        <div className="tutorial-dots">
          {STEPS.map((_, i) => (
            <span key={i} className={`tutorial-dot${i === step ? ' active' : ''}`} onClick={() => setStep(i)} />
          ))}
        </div>

        <div className="tutorial-actions">
          {step > 0 && (
            <button className="btn-secondary" onClick={() => setStep(s => s - 1)}>← Back</button>
          )}
          {!isLast && (
            <button className="btn-primary" onClick={() => setStep(s => s + 1)}>Next →</button>
          )}
          {isLast && (
            <button className="btn-primary" onClick={handleDismiss}>Get Started →</button>
          )}
          <button className="btn-skip" onClick={handleDismiss}>Skip tutorial</button>
        </div>
      </div>
    </div>
  );
}
