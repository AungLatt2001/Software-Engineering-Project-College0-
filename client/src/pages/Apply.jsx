import React, { useState } from 'react';
import api from '../api';

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
        <p>Submit your application to join as a student or instructor.</p>
      </div>

      <div className="form-card">
        {success && <div className="alert alert-success">✓ Application submitted! The Registrar will review it shortly.</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <div className="info-box">Students require a prior GPA &gt; 3.0 for admission. A registrar will review all applications.</div>

        <form onSubmit={submit}>
          <div className="form-group">
            <label>Full Name</label>
            <input value={form.name} onChange={set('name')} placeholder="Your full name" required />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.email} onChange={set('email')} placeholder="email@example.com" required />
          </div>
          <div className="form-group">
            <label>Applying As</label>
            <select value={form.role} onChange={set('role')}>
              <option value="student">Student</option>
              <option value="instructor">Instructor</option>
            </select>
          </div>
          <div className="form-group">
            <label>Prior GPA (0.0 – 4.0)</label>
            <input type="number" value={form.gpa} onChange={set('gpa')} min="0" max="4" step="0.001" placeholder="e.g. 3.750" />
          </div>
          <div className="form-group">
            <label>Statement <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional)</span></label>
            <textarea value={form.statement} onChange={set('statement')} placeholder="Why do you want to join College0?" />
          </div>
          <button type="submit" className="btn-primary btn-block" disabled={busy}>
            {busy ? 'Submitting…' : 'Submit Application'}
          </button>
        </form>
      </div>
    </>
  );
}
