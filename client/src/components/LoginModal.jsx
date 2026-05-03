import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import api from '../api';

export default function LoginModal() {
  const { loginOpen, setLoginOpen, setUser, setSem } = useAuth();
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const submit = async e => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const r = await api.post('/login', { email, password: pw });
      setUser(r.data.user);
      setSem(r.data.sem);
      setLoginOpen(false);
      setEmail(''); setPw('');
      const role = r.data.user.role;
      if (role === 'student') nav('/dashboard');
      else if (role === 'instructor') nav('/instructor');
      else nav('/registrar');
    } catch (err) {
      setError('Invalid email or password.');
    } finally { setBusy(false); }
  };

  if (!loginOpen) return null;

  return (
    <div className="modal-overlay open" onClick={e => { if (e.target === e.currentTarget) setLoginOpen(false); }}>
      <div className="modal-card">
        <button className="modal-close" onClick={() => setLoginOpen(false)}>&times;</button>
        <div className="modal-logo">College0</div>
        <h2 className="modal-title">Sign In</h2>
        <p className="modal-sub">Access your academic portal.</p>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="demo-box">
          <strong>Demo</strong> — password: <code>Password123!</code><br />
          <strong>Students:</strong> liam.turner@college0.edu, priya.sharma@college0.edu<br />
          <strong>Instructor:</strong> alan.brooks@college0.edu &nbsp;
          <strong>Registrar:</strong> diana.morgan@college0.edu
        </div>

        <form onSubmit={submit}>
          <div className="form-group">
            <label>Email Address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="your.email@college0.edu" required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={pw} onChange={e => setPw(e.target.value)}
              placeholder="Password" required />
          </div>
          <button type="submit" className="btn-primary btn-block" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign In →'}
          </button>
        </form>
      </div>
    </div>
  );
}
