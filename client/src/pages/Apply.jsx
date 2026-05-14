import React, { useState } from 'react';
import api from '../api';

const PROCESS_STEPS = [
  { icon: '📝', title: 'Fill out the form', desc: 'Provide your name, email, role, prior GPA, and a short statement.' },
  { icon: '📬', title: 'Application submitted', desc: 'Your application is sent to the Registrar for review.' },
  { icon: '✅', title: 'Registrar reviews', desc: 'A Registrar will approve or reject your application — usually within a few days.' },
  { icon: '🔑', title: 'Receive credentials', desc: 'If approved, you\'ll receive your college email and a temporary password to log in.' },
];

export default function Apply() {
  const [form, setForm] = useState({ name: '', email: '', role: 'student', gpa: '', statement: '' });
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const submit = async e => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      await api.post('/apply', form);
      setSuccess(true);
      setForm({ name: '', email: '', role: 'student', gpa: '', statement: '' });
    } catch (err) {
      setError(err.response?.data?.error || 'Submission failed. Please try again.');
    } finally { setBusy(false); }
  };

  return (
    <>
      <div className="page-header">
        <h1>Apply to College0</h1>
        <p>Submit a visitor application to join as a prospective student or instructor.</p>
      </div>

      {/* Process overview */}
      <div className="apply-process">
        {PROCESS_STEPS.map((s, i) => (
          <div className="apply-process-step" key={i}>
            <div className="apply-process-icon">{s.icon}</div>
            <div className="apply-process-num">Step {i + 1}</div>
            <div className="apply-process-title">{s.title}</div>
            <div className="apply-process-desc">{s.desc}</div>
          </div>
        ))}
      </div>

      {/* Requirements callout */}
      <div className="apply-reqs">
        <div className="apply-reqs-col">
          <div className="apply-reqs-heading">🎓 Student Requirements</div>
          <ul className="apply-reqs-list">
            <li>Prior GPA of <strong>3.0 or higher</strong> from previous institution</li>
            <li>Valid email address</li>
            <li>Optional personal statement (recommended)</li>
          </ul>
        </div>
        <div className="apply-reqs-col">
          <div className="apply-reqs-heading">📚 Instructor Requirements</div>
          <ul className="apply-reqs-list">
            <li>Relevant subject-matter expertise</li>
            <li>Valid email address</li>
            <li>Statement of teaching interest (recommended)</li>
            <li>GPA not required for instructors</li>
          </ul>
        </div>
      </div>

      {/* Form */}
      <div className="form-card" style={{ maxWidth: 580 }}>
        <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 18 }}>Application Form</div>

        {success && (
          <div className="alert alert-success" style={{ marginBottom: 18 }}>
            ✓ Application submitted! A Registrar will review it and contact you at the email provided.
          </div>
        )}
        {error && <div className="alert alert-error" style={{ marginBottom: 18 }}>{error}</div>}

        <form onSubmit={submit}>
          <div className="form-group">
            <label>Full Name</label>
            <input value={form.name} onChange={set('name')} placeholder="Your full legal name" required />
          </div>
          <div className="form-group">
            <label>Email Address</label>
            <input type="email" value={form.email} onChange={set('email')} placeholder="your@email.com" required />
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 4 }}>
              Your college email and login credentials will be sent here if approved.
            </div>
          </div>
          <div className="form-group">
            <label>Applying As</label>
            <select value={form.role} onChange={set('role')}>
              <option value="student">Student — enroll in courses, track GPA, apply for graduation</option>
              <option value="instructor">Instructor — teach courses, post grades, manage students</option>
            </select>
          </div>
          <div className="form-group">
            <label>
              Prior GPA (0.0 – 4.0)
              {form.role === 'student' && <span style={{ color: 'var(--red)', marginLeft: 6, fontSize: '0.72rem' }}>* Required — must be ≥ 3.0</span>}
              {form.role === 'instructor' && <span style={{ color: 'var(--muted)', marginLeft: 6, fontSize: '0.72rem' }}>Optional for instructors</span>}
            </label>
            <input
              type="number"
              value={form.gpa}
              onChange={set('gpa')}
              min="0" max="4" step="0.001"
              placeholder="e.g. 3.750"
              required={form.role === 'student'}
            />
          </div>
          <div className="form-group">
            <label>Personal Statement <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional but recommended)</span></label>
            <textarea
              value={form.statement}
              onChange={set('statement')}
              placeholder={form.role === 'student'
                ? 'Tell us about your academic background and why you want to join College0...'
                : 'Describe your teaching experience and which courses you\'d like to teach...'
              }
              style={{ minHeight: 110 }}
            />
          </div>
          <button type="submit" className="btn-primary btn-block" disabled={busy} style={{ padding: '11px', fontSize: '0.9rem' }}>
            {busy ? 'Submitting…' : 'Submit Application'}
          </button>
        </form>

        <div style={{ marginTop: 18, padding: '12px 14px', background: '#f8f9fb', borderRadius: 8, fontSize: '0.75rem', color: 'var(--muted)', lineHeight: 1.6 }}>
          By submitting this form you agree that your information may be reviewed by College0 administrators.
          Applications are typically reviewed within 2–3 business days.
        </div>
      </div>
    </>
  );
}
