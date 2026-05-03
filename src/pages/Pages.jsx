// client/src/pages/Pages.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth, api } from '../context/AuthContext';
import { StatCard, Badge, Alert, Spinner, Table, Tabs, Modal, InfoCard } from '../components/UI';

// ══════════════════════════════════════════════════
// HOME PAGE
// ══════════════════════════════════════════════════
export function HomePage({ onLogin }) {
  const [data, setData] = useState(null);
  useEffect(() => { api.get('/public').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <Spinner />;

  const gradeColor = v => v >= 3.7 ? 'var(--green)' : v >= 3.0 ? 'var(--navy)' : v >= 2.0 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div>
      <div className="hero-banner">
        <h1 className="hero-title">Welcome to College0</h1>
        <p className="hero-sub">An AI-enabled academic management portal for students, instructors, and administrators.</p>
        <div className="hero-chips">
          {[
            ['CURRENT PHASE', data.phaseLabel],
            ['SEMESTER', `#${data.semester}`],
            ['STUDENTS', data.studentCount],
            ['COURSES', data.activeCoursesCount],
          ].map(([label, val]) => (
            <div key={label} className="hero-chip">
              <div className="hero-chip-label">{label}</div>
              <div className="hero-chip-value">{val}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid-4 gap-16" style={{ marginBottom: 20 }}>
        <StatCard label="Enrolled Students" value={data.studentCount} sub="Active this semester" variant="navy" />
        <StatCard label="Active Courses"    value={data.activeCoursesCount} sub="Available" variant="green" />
        <StatCard label="Campus Avg GPA"    value={data.avgGpa} sub="All students" variant="warn" />
        <StatCard label="Faculty"           value={data.instructorCount} sub="Instructors" variant="navy" />
      </div>

      <div className="grid-3 gap-16" style={{ marginBottom: 24 }}>
        <InfoCard title="🏆 Top Rated Courses" accent="var(--green)"
          items={data.topRated.map(c => `${c.code} — ${c.name} · ${c.rating} ★`)} />
        <InfoCard title="📉 Needs Improvement" accent="var(--warning)"
          items={data.lowestRated.map(c => `${c.code} — ${c.name} · ${c.rating} ★`)} />
        <InfoCard title="🎓 Top GPA Students" accent="var(--navy)"
          items={data.topGpa.map(s => `${s.name} (${s.userId}) — ${s.gpa}`)} />
      </div>

      <div className="section-title">Course Catalogue</div>
      <Table
        headers={['Code', 'Course Name', 'Instructor', 'Time', 'Enrolled', 'Core', 'Rating', 'Status']}
        rows={data.courses.map(c => [
          c.code, c.name, c.instructorId || '—', c.timeSlot,
          `${c.enrolled}/${c.capacity}`,
          c.isCore ? '★ Core' : '',
          c.rating ? `${c.rating} ★` : '—',
          c.cancelled ? 'Cancelled' : c.enrolled >= c.capacity ? 'Waitlist' : 'Available'
        ])}
        colorFn={(val, ci) => {
          if (ci === 7) return val === 'Available' ? 'var(--green)' : val === 'Cancelled' ? 'var(--danger)' : 'var(--warning)';
          return null;
        }}
      />

      {!useAuth().user && (
        <div style={{ textAlign: 'center', marginTop: 32 }}>
          <button className="btn btn-primary" onClick={onLogin}>Sign In to Access Your Portal</button>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════
// LOGIN MODAL  (overlay — never hides the home page)
// ══════════════════════════════════════════════════
export function LoginModal({ onSuccess, onClose }) {
  const { login, changePassword } = useAuth();
  const [form, setForm] = useState({ userId: '', password: '' });
  const [newPw, setNewPw] = useState({ pw1: '', pw2: '' });
  const [firstLogin, setFirstLogin] = useState(false);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  // Close on Escape key
  React.useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleLogin = async e => {
    e.preventDefault(); setErr(''); setLoading(true);
    try {
      const res = await login(form.userId, form.password);
      if (res.firstLogin) { setFirstLogin(true); }
      else { onSuccess(res.user); }
    } catch (e) { setErr(e.response?.data?.error || 'Login failed.'); }
    setLoading(false);
  };

  const handleChangePw = async e => {
    e.preventDefault(); setErr('');
    if (newPw.pw1 !== newPw.pw2) { setErr('Passwords do not match.'); return; }
    if (newPw.pw1.length < 4) { setErr('Minimum 4 characters.'); return; }
    try {
      await changePassword(newPw.pw1);
      const u = JSON.parse(localStorage.getItem('college0_user'));
      onSuccess(u);
    } catch { setErr('Failed to change password.'); }
  };

  const overlayStyle = {
    position: 'fixed', inset: 0,
    background: 'rgba(26,45,90,0.55)',
    backdropFilter: 'blur(3px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000, padding: 20,
  };

  const cardStyle = {
    background: 'var(--surface)',
    borderRadius: 14,
    padding: 36,
    width: '100%',
    maxWidth: 420,
    boxShadow: '0 20px 60px rgba(26,45,90,0.25)',
    position: 'relative',
  };

  const closeBtnStyle = {
    position: 'absolute', top: 14, right: 16,
    background: 'none', border: 'none',
    fontSize: 22, cursor: 'pointer',
    color: 'var(--text3)', lineHeight: 1,
    padding: '2px 6px', borderRadius: 6,
    transition: 'background 0.15s',
  };

  if (firstLogin) return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={cardStyle} onClick={e => e.stopPropagation()}>
        <button style={closeBtnStyle} onClick={onClose} title="Back to home">×</button>
        <div className="login-logo">College0</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4, marginTop: 8 }}>Set New Password</h2>
        <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 16 }}>You must change your password before continuing.</p>
        <div className="divider" />
        {err && <Alert variant="danger">{err}</Alert>}
        <form onSubmit={handleChangePw}>
          <div className="form-group">
            <label className="form-label">New Password</label>
            <input className="form-input" type="password" placeholder="New password" value={newPw.pw1} onChange={e => setNewPw(p => ({ ...p, pw1: e.target.value }))} required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">Confirm Password</label>
            <input className="form-input" type="password" placeholder="Confirm" value={newPw.pw2} onChange={e => setNewPw(p => ({ ...p, pw2: e.target.value }))} required />
          </div>
          <button className="btn btn-primary btn-full" type="submit">Save Password</button>
        </form>
      </div>
    </div>
  );

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={cardStyle} onClick={e => e.stopPropagation()}>
        {/* Close / back button */}
        <button style={closeBtnStyle} onClick={onClose} title="Back to home">×</button>

        <div className="login-logo">College0</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4, marginTop: 8 }}>Sign In</h2>
        <p style={{ fontSize: 13, color: 'var(--text2)' }}>Access your academic portal.</p>
        <div className="divider" />

        {err && <Alert variant="danger">{err}</Alert>}

        <div className="alert alert-info" style={{ marginBottom: 14 }}>
          <strong>Demo credentials</strong> — all passwords: <code>pass123</code><br />
          Students: S101–S110 · Instructors: I01–I03 · Registrar: REG01 / <code>admin</code>
        </div>

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">User ID</label>
            <input className="form-input" placeholder="e.g. S101, I01, REG01" value={form.userId} onChange={e => setForm(f => ({ ...f, userId: e.target.value }))} required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input className="form-input" type="password" placeholder="Password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
          </div>
          <button className="btn btn-primary btn-full" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In →'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 13, cursor: 'pointer', textDecoration: 'underline' }}
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════
// APPLY PAGE
// ══════════════════════════════════════════════════
export function ApplyPage() {
  const [form, setForm] = useState({ name: '', email: '', role: 'Student', gpa: '', notes: '' });
  const [msg, setMsg] = useState(null);

  const submit = async e => {
    e.preventDefault(); setMsg(null);
    try {
      const res = await api.post('/apply', form);
      setMsg({ ok: true, text: `Application submitted! ID: ${res.data.appId}. A registrar will review shortly.` });
      setForm({ name: '', email: '', role: 'Student', gpa: '', notes: '' });
    } catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Submission failed.' }); }
  };

  return (
    <div style={{ maxWidth: 520, margin: '0 auto' }}>
      <div className="page-header">
        <h1 className="page-title">Apply to College0</h1>
        <p className="page-subtitle">Submit your application to join as a student or instructor.</p>
      </div>
      <div className="card">
        {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
        <Alert variant="info">Students require GPA &gt; 3.0 for admission. A registrar will review all applications.</Alert>
        <form onSubmit={submit} style={{ marginTop: 16 }}>
          {[['Full Name','name','text','Your full name'],['Email','email','email','email@example.com']].map(([label,key,type,ph]) => (
            <div className="form-group" key={key}>
              <label className="form-label">{label}</label>
              <input className="form-input" type={type} placeholder={ph} value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} required />
            </div>
          ))}
          <div className="form-group">
            <label className="form-label">Applying As</label>
            <select className="form-input" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              <option>Student</option><option>Instructor</option>
            </select>
          </div>
          {form.role === 'Student' && (
            <div className="form-group">
              <label className="form-label">Current GPA (0.0 – 4.0)</label>
              <input className="form-input" type="number" step="0.01" min="0" max="4" placeholder="e.g. 3.75" value={form.gpa} onChange={e => setForm(f => ({ ...f, gpa: e.target.value }))} required />
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Statement (optional)</label>
            <textarea className="form-input" placeholder="Why do you want to join?" value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          </div>
          <button className="btn btn-primary btn-full" type="submit">Submit Application</button>
        </form>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════
// STUDENT PAGES
// ══════════════════════════════════════════════════
export function StudentDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => { api.get('/student/me').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <Spinner />;

  const gpaColor = g => g >= 3.0 ? 'var(--green)' : g >= 2.0 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div>
      <div className="hero-banner" style={{ marginBottom: 20 }}>
        <div className="flex items-center gap-12" style={{ marginBottom: 8 }}>
          <h1 className="hero-title" style={{ marginBottom: 0 }}>Welcome back, {data.name}</h1>
          {data.graduated && <span className="badge badge-green">GRADUATED 🎓</span>}
          {data.suspended && <span className="badge badge-danger">SUSPENDED</span>}
          {data.honorCount > 0 && <span className="badge badge-warning">🏅 Honor Roll ×{data.honorCount}</span>}
        </div>
        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>{data.userId} · Student Portal</p>
        <div className="hero-chips" style={{ marginTop: 20 }}>
          <div className="hero-chip">
            <div className="hero-chip-label">GPA</div>
            <div className="hero-chip-value" style={{ color: data.gpa >= 3.0 ? '#5CDB95' : data.gpa >= 2.0 ? '#FFD700' : '#FF6B6B' }}>{data.gpa}</div>
          </div>
          <div className="hero-chip"><div className="hero-chip-label">WARNINGS</div><div className="hero-chip-value">{data.warnings}/3</div></div>
          <div className="hero-chip"><div className="hero-chip-label">ENROLLED</div><div className="hero-chip-value">{data.currentEnrollment?.length || 0}</div></div>
          <div className="hero-chip"><div className="hero-chip-label">COMPLETED</div><div className="hero-chip-value">{data.completedCourses?.length || 0}</div></div>
        </div>
      </div>

      {data.semestersCompleted <= 1 && !data.currentEnrollment?.length && (
        <Alert variant="info">
          👋 <strong>Welcome!</strong> Register for 2–4 courses during Registration phase · Maintain GPA &gt; 2.25 · Submit reviews during Grading phase (before grade is posted).
        </Alert>
      )}

      {data.warnings > 0 && (
        <Alert variant="warning">⚠️ You have {data.warnings} warning(s). 3 warnings result in suspension.</Alert>
      )}
    </div>
  );
}

export function StudentCourses() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState(null);
  const { user } = useAuth();

  const load = useCallback(() => { api.get('/student/courses').then(r => setData(r.data)).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const register = async code => {
    try { const r = await api.post('/student/register', { courseCode: code }); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const drop = async code => {
    try { const r = await api.post('/student/drop', { courseCode: code }); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!data) return <Spinner />;
  const regOpen = data.phase === 'REGISTRATION' || (data.phase === 'RUNNING' && data.specialRegistration);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">My Courses</h1>
        <p className="page-subtitle">Manage your course registrations for this semester.</p>
      </div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      {data.specialRegistration && data.phase === 'RUNNING' && (
        <Alert variant="warning">⚡ <strong>Special Registration Period</strong> — One or more courses were cancelled. You may register for replacements below.</Alert>
      )}

      <div className="section-title">Enrolled This Semester</div>
      {data.enrolled.length ? (
        <Table
          headers={['Code', 'Course Name', 'Time Slot', 'Instructor', '']}
          rows={data.enrolled.map(c => [c.code, c.name, c.timeSlot, c.instructorId || '—',
            data.phase === 'REGISTRATION'
              ? <button key={c.code} className="btn btn-danger btn-sm" onClick={() => drop(c.code)}>Drop</button>
              : '—'
          ])}
        />
      ) : (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text3)', padding: 32 }}>
          No courses enrolled this semester.
        </div>
      )}

      <div className="divider" style={{ margin: '24px 0' }} />

      {regOpen ? (
        <>
          <div className="section-title">Register for a Course</div>
          <Table
            headers={['Code', 'Name', 'Time Slot', 'Seats', 'Core', '']}
            rows={data.available.map(c => [
              c.code, c.name, c.timeSlot,
              c.enrolled.length >= c.capacity ? 'FULL' : `${c.capacity - c.enrolled.length} left`,
              c.isCore ? '★' : '',
              <button key={c.code} className="btn btn-primary btn-sm" onClick={() => register(c.code)}>
                {c.enrolled.length >= c.capacity ? 'Join Waitlist' : 'Register'}
              </button>
            ])}
            colorFn={(val, ci) => ci === 3 && val === 'FULL' ? 'var(--danger)' : null}
          />
        </>
      ) : (
        <Alert variant="info">Registration is closed (Phase: {data.phase}). Registrations open during the Registration period.</Alert>
      )}
    </div>
  );
}

export function StudentGrades() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get('/student/grades').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <Spinner />;

  const gradeColor = g => {
    const pts = { 'A+':4,'A':4,'A-':3.7,'B+':3.3,'B':3,'B-':2.7,'C+':2.3,'C':2,'C-':1.7,'D':1,'F':0 };
    const p = pts[g] ?? 2;
    return p >= 3.7 ? 'var(--green)' : p >= 3.0 ? 'var(--navy)' : p >= 2.0 ? 'var(--warning)' : 'var(--danger)';
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Academic Transcript</h1>
        <p className="page-subtitle">Your complete grade history and academic standing.</p>
      </div>
      <div className="grid-3 gap-16" style={{ marginBottom: 24 }}>
        <StatCard label="Cumulative GPA" value={data.gpa} variant={data.gpa >= 3.0 ? 'green' : data.gpa >= 2.0 ? 'warn' : 'danger'} />
        <StatCard label="Warnings" value={`${data.warnings}/3`} variant={data.warnings > 0 ? 'danger' : 'navy'} />
        <StatCard label="Honor Count" value={data.honorCount} variant="green" sub="Each removes 1 warning" />
      </div>
      {data.grades.length ? (
        <Table
          headers={['Course Code', 'Course Name', 'Grade', 'Points', 'Semester']}
          rows={data.grades.sort((a,b) => a.semester - b.semester).map(g => [
            g.courseCode, g.courseName, g.grade,
            ({ 'A+':4,'A':4,'A-':3.7,'B+':3.3,'B':3,'B-':2.7,'C+':2.3,'C':2,'C-':1.7,'D':1,'F':0 }[g.grade] ?? 0).toFixed(1),
            `Semester ${g.semester}`
          ])}
          colorFn={(val, ci) => ci === 2 ? gradeColor(val) : null}
        />
      ) : (
        <div className="empty-state">No grade history yet.</div>
      )}
    </div>
  );
}

export function StudentActions() {
  const [tab, setTab] = useState('review');
  const [courses, setCourses] = useState([]);
  const [me, setMe] = useState(null);
  const [msg, setMsg] = useState(null);
  const [review, setReview] = useState({ courseCode: '', text: '', rating: 5 });
  const [complaint, setComplaint] = useState({ againstId: '', description: '' });

  useEffect(() => {
    api.get('/student/courses').then(r => setCourses(r.data.enrolled || []));
    api.get('/student/me').then(r => setMe(r.data));
  }, []);

  const submitReview = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/student/review', review); setMsg({ ok: r.data.ok, text: r.data.msg }); setReview(v => ({ ...v, text: '' })); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const submitGraduation = async () => {
    setMsg(null);
    try { const r = await api.post('/student/graduate'); setMsg({ ok: r.data.ok, text: r.data.msg }); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const submitComplaint = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/student/complaint', complaint); setMsg({ ok: r.data.ok, text: `Complaint ${r.data.complaintId} filed.` }); setComplaint({ againstId: '', description: '' }); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!me) return <Spinner />;
  const total = new Set(me.completedCourses || []).size;
  const coreRequired = ['CSC 10100','CSC 10200','CSC 21700','CSC 22000'];
  const coreDone = coreRequired.filter(c => (me.completedCourses || []).includes(c)).length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Reviews, Graduation & Complaints</h1>
      </div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: 'review', label: '✍️ Course Review' },
        { id: 'graduation', label: '🎓 Graduation' },
        { id: 'complaint', label: '📣 Complaint' },
      ]} />

      {tab === 'review' && (
        <div className="card">
          <div className="section-title">Submit a Course Review</div>
          <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 16 }}>Reviews are anonymous. Only available during Grading period, before your grade is posted.</p>
          <form onSubmit={submitReview}>
            <div className="form-group">
              <label className="form-label">Course</label>
              <select className="form-input" value={review.courseCode} onChange={e => setReview(r => ({ ...r, courseCode: e.target.value }))} required>
                <option value="">Select a course...</option>
                {courses.map(c => <option key={c.code} value={c.code}>{c.code} — {c.name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Rating</label>
              <select className="form-input" value={review.rating} onChange={e => setReview(r => ({ ...r, rating: parseInt(e.target.value) }))}>
                {[5,4,3,2,1].map(n => <option key={n} value={n}>{n} {'★'.repeat(n)} — {['','Poor','Below Average','Average','Good','Excellent'][n]}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Review Text</label>
              <textarea className="form-input" placeholder="Share your feedback (anonymous)..." value={review.text} onChange={e => setReview(r => ({ ...r, text: e.target.value }))} required />
            </div>
            <button className="btn btn-primary" type="submit">Submit Review</button>
          </form>
        </div>
      )}

      {tab === 'graduation' && (
        <div className="card">
          <div className="section-title">Graduation Application</div>
          <Table
            headers={['Requirement', 'Your Status', 'Met?']}
            rows={[
              ['Total Courses', `${total} / 8`, total >= 8 ? '✅' : '❌'],
              ['Core Courses', `${coreDone} / 4`, coreDone === 4 ? '✅' : '❌'],
              ['Min GPA ≥ 2.0', `${me.gpa}`, me.gpa >= 2.0 ? '✅' : '❌'],
            ]}
            colorFn={(val, ci) => ci === 2 ? (val === '✅' ? 'var(--green)' : 'var(--danger)') : null}
          />
          {me.graduated ? (
            <div className="alert alert-success" style={{ marginTop: 16 }}>🎓 You have graduated!</div>
          ) : (
            <button className="btn btn-green" style={{ marginTop: 16 }} onClick={submitGraduation}>
              Apply for Graduation
            </button>
          )}
          <p style={{ fontSize: 12, color: 'var(--text3)', marginTop: 10 }}>⚠️ Applying without meeting all requirements results in a warning (reckless application).</p>
        </div>
      )}

      {tab === 'complaint' && (
        <div className="card">
          <div className="section-title">File a Complaint</div>
          <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 16 }}>You may report another student or an instructor. The registrar will investigate.</p>
          <form onSubmit={submitComplaint}>
            <div className="form-group">
              <label className="form-label">User ID of Person You're Reporting</label>
              <input className="form-input" placeholder="e.g. S102 or I01" value={complaint.againstId} onChange={e => setComplaint(c => ({ ...c, againstId: e.target.value }))} required />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea className="form-input" placeholder="Describe the issue in detail..." value={complaint.description} onChange={e => setComplaint(c => ({ ...c, description: e.target.value }))} required />
            </div>
            <button className="btn btn-warning" type="submit">Submit Complaint</button>
          </form>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════
// INSTRUCTOR PAGES
// ══════════════════════════════════════════════════
export function InstructorDashboard() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get('/instructor/me').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <Spinner />;
  const { instructor: inst, courses } = data;

  return (
    <div>
      <div className="hero-banner" style={{ marginBottom: 20 }}>
        <h1 className="hero-title">Welcome, {inst.name}</h1>
        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>{inst.userId} · {inst.suspended ? '⛔ Suspended' : '✅ Active Instructor'}</p>
        <div className="hero-chips" style={{ marginTop: 20 }}>
          <div className="hero-chip"><div className="hero-chip-label">ACTIVE COURSES</div><div className="hero-chip-value">{courses.length}</div></div>
          <div className="hero-chip"><div className="hero-chip-label">TOTAL STUDENTS</div><div className="hero-chip-value">{courses.reduce((s,c) => s + c.enrolled.length, 0)}</div></div>
          <div className="hero-chip"><div className="hero-chip-label">WARNINGS</div><div className="hero-chip-value">{inst.warnings}/3</div></div>
        </div>
      </div>
      <div className="section-title">My Assigned Courses</div>
      {courses.map(c => (
        <div key={c.code} className="card" style={{ marginBottom: 12, borderLeft: '3px solid var(--navy)' }}>
          <div className="flex items-center gap-16">
            <strong>{c.code}</strong>
            <span style={{ color: 'var(--text2)' }}>{c.name}</span>
            <span style={{ color: 'var(--text3)', fontSize: 12 }}>{c.timeSlot}</span>
            <span style={{ color: 'var(--navy)', fontSize: 13, marginLeft: 'auto' }}>{c.enrolled.length}/{c.capacity} students</span>
            {c.waitlist.length > 0 && <Badge variant="warning">+{c.waitlist.length} waitlist</Badge>}
            {c.cancelled && <Badge variant="danger">CANCELLED</Badge>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function InstructorCourses() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState(null);
  const load = useCallback(() => { api.get('/instructor/me').then(r => setData(r.data)).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const admit = async courseCode => {
    try { const r = await api.post('/instructor/admit-waitlist', { courseCode }); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: 'Error' }); }
  };

  if (!data) return <Spinner />;
  return (
    <div>
      <div className="page-header"><h1 className="page-title">My Classes</h1></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      {data.courses.map(c => (
        <div key={c.code} style={{ marginBottom: 24 }}>
          <div className="flex items-center gap-12" style={{ marginBottom: 10 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--navy)' }}>{c.code} — {c.name}</h3>
            <span style={{ fontSize: 12, color: 'var(--text3)' }}>[{c.timeSlot}]</span>
          </div>
          <Table
            headers={['Student ID', 'Name', 'GPA', 'Warnings', 'Current Grade']}
            rows={(c.students || []).map(s => [s.userId, s.name, s.gpa, s.warnings, s.grade || '—'])}
            colorFn={(val, ci) => ci === 4 ? (val === '—' ? 'var(--text3)' : null) : null}
          />
          {c.waitlist?.length > 0 && (
            <div className="alert alert-warning" style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span>⏳ {c.waitlist.length} student(s) on waitlist</span>
              <button className="btn btn-primary btn-sm" onClick={() => admit(c.code)}>Admit Next</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function InstructorGrades() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ studentId: '', courseCode: '', grade: 'A' });
  const [msg, setMsg] = useState(null);
  const load = useCallback(() => { api.get('/instructor/me').then(r => setData(r.data)).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/instructor/grade', form); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!data) return <Spinner />;
  const allStudents = data.courses.flatMap(c => (c.students || []).map(s => ({ ...s, courseCode: c.code, courseName: c.name })));

  return (
    <div>
      <div className="page-header"><h1 className="page-title">Submit Grades</h1></div>
      {data.phase !== 'GRADING' && <Alert variant="warning">Grade submission only available during the Grading phase. Current: {data.phase}</Alert>}
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Table
        headers={['Student', 'Course', 'Current Grade']}
        rows={allStudents.map(s => [s.name, s.courseCode, s.grade || '—'])}
        colorFn={(val, ci) => ci === 2 && val === '—' ? 'var(--warning)' : null}
      />
      {data.phase === 'GRADING' && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="section-title">Submit a Grade</div>
          <form onSubmit={submit}>
            <div className="grid-3 gap-12">
              <div className="form-group">
                <label className="form-label">Student</label>
                <select className="form-input" value={`${form.studentId}|${form.courseCode}`} onChange={e => { const [s,c] = e.target.value.split('|'); setForm(f => ({ ...f, studentId: s, courseCode: c })); }} required>
                  <option value="">Select student...</option>
                  {allStudents.map(s => <option key={`${s.userId}|${s.courseCode}`} value={`${s.userId}|${s.courseCode}`}>{s.name} ({s.courseCode})</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Grade</label>
                <select className="form-input" value={form.grade} onChange={e => setForm(f => ({ ...f, grade: e.target.value }))}>
                  {['A+','A','A-','B+','B','B-','C+','C','C-','D','F'].map(g => <option key={g}>{g}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                <button className="btn btn-primary" type="submit" style={{ marginTop: 21 }}>Submit Grade</button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export function InstructorComplaints() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ againstId: '', description: '' });
  const [msg, setMsg] = useState(null);
  useEffect(() => { api.get('/instructor/me').then(r => setData(r.data)).catch(() => {}); }, []);

  const submit = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/instructor/complaint', form); setMsg({ ok: true, text: `Complaint ${r.data.complaintId} filed.` }); setForm({ againstId: '', description: '' }); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!data) return <Spinner />;
  const allStudents = data.courses.flatMap(c => c.students || []);

  return (
    <div>
      <div className="page-header"><h1 className="page-title">File a Complaint</h1><p className="page-subtitle">Report a student to the registrar for investigation.</p></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <div className="card">
        <form onSubmit={submit}>
          <div className="form-group">
            <label className="form-label">Student</label>
            <select className="form-input" value={form.againstId} onChange={e => setForm(f => ({ ...f, againstId: e.target.value }))} required>
              <option value="">Select student...</option>
              {allStudents.map(s => <option key={s.userId} value={s.userId}>{s.userId} — {s.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-input" placeholder="Describe the issue..." value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} required />
          </div>
          <Alert variant="info">Instructor complaints against students require mandatory registrar action. Unjustified complaints may result in a warning to you.</Alert>
          <button className="btn btn-warning" type="submit">Submit Complaint</button>
        </form>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════
// REGISTRAR PAGES
// ══════════════════════════════════════════════════
export function RegistrarDashboard() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState(null);
  const load = useCallback(() => { api.get('/registrar/overview').then(r => setData(r.data)).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const advance = async () => {
    try { const r = await api.post('/registrar/advance-phase'); setMsg({ ok: true, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: 'Error advancing phase.' }); }
  };
  const closeSpecialReg = async () => {
    try { await api.post('/registrar/close-special-reg'); setMsg({ ok: true, text: 'Special registration closed.' }); load(); }
    catch { }
  };

  if (!data) return <Spinner />;

  return (
    <div>
      <div className="page-header"><h1 className="page-title">Registrar Overview</h1><p className="page-subtitle">Full administrative access to all system operations.</p></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'} ><pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 12 }}>{msg.text}</pre></Alert>}

      <div className="card" style={{ borderLeft: '4px solid var(--navy)', marginBottom: 20 }}>
        <div className="flex items-center gap-16" style={{ flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--navy)' }}>Phase: {data.phaseLabel}</div>
            <div style={{ fontSize: 12, color: 'var(--text3)' }}>Semester #{data.semester}</div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {data.specialRegistration && (
              <button className="btn btn-warning" onClick={closeSpecialReg}>Close Special Registration</button>
            )}
            <button className="btn btn-primary" onClick={advance}>Advance Phase →</button>
          </div>
        </div>
      </div>

      {data.specialRegistration && <Alert variant="warning">⚡ Special registration period is currently open.</Alert>}

      <div className="grid-4 gap-16">
        <StatCard label="Active Students"      value={data.studentCount}    variant="navy" />
        <StatCard label="Pending Applications" value={data.pendingApps}     variant={data.pendingApps > 0 ? 'warn' : 'navy'} />
        <StatCard label="Open Complaints"      value={data.openComplaints}  variant={data.openComplaints > 0 ? 'danger' : 'navy'} />
        <StatCard label="Active Courses"       value={data.activeCourses}   variant="green" />
      </div>
    </div>
  );
}

export function RegistrarCourses() {
  const [courses, setCourses] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [form, setForm] = useState({ code: '', name: '', instructorId: '', timeSlot: '', capacity: 20, isCore: false });
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    api.get('/registrar/courses').then(r => setCourses(r.data));
    api.get('/registrar/instructors').then(r => setInstructors(r.data));
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/registrar/create-course', form); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  return (
    <div>
      <div className="page-header"><h1 className="page-title">Manage Courses</h1></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Table
        headers={['Code', 'Name', 'Instructor', 'Time', 'Enrolled', 'Core', 'Status']}
        rows={courses.map(c => [
          c.code, c.name, c.instructorId || '—', c.timeSlot,
          `${c.enrolled.length}/${c.capacity}`,
          c.isCore ? '★' : '',
          c.cancelled ? 'Cancelled' : 'Active'
        ])}
        colorFn={(val, ci) => ci === 6 ? (val === 'Cancelled' ? 'var(--danger)' : 'var(--green)') : null}
      />
      <div className="card" style={{ marginTop: 24 }}>
        <div className="section-title">Create New Course</div>
        <form onSubmit={create}>
          <div className="grid-3 gap-12">
            {[['Code','code','e.g. CSC 40000'],['Name','name','Course name'],['Time Slot','timeSlot','e.g. MWF 9-10']].map(([l,k,p]) => (
              <div className="form-group" key={k}><label className="form-label">{l}</label>
                <input className="form-input" placeholder={p} value={form[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} required /></div>
            ))}
            <div className="form-group"><label className="form-label">Instructor</label>
              <select className="form-input" value={form.instructorId} onChange={e => setForm(f => ({ ...f, instructorId: e.target.value }))} required>
                <option value="">Select...</option>
                {instructors.map(i => <option key={i.userId} value={i.userId}>{i.userId} — {i.name}</option>)}
              </select>
            </div>
            <div className="form-group"><label className="form-label">Capacity</label>
              <input className="form-input" type="number" min="3" max="60" value={form.capacity} onChange={e => setForm(f => ({ ...f, capacity: parseInt(e.target.value) }))} /></div>
            <div className="form-group"><label className="form-label">Core Course</label>
              <select className="form-input" value={form.isCore} onChange={e => setForm(f => ({ ...f, isCore: e.target.value === 'true' }))}>
                <option value="false">No</option><option value="true">Yes ★</option>
              </select>
            </div>
          </div>
          <button className="btn btn-green" type="submit">Create Course</button>
        </form>
      </div>
    </div>
  );
}

export function RegistrarStudents() {
  const [students, setStudents] = useState([]);
  const [warn, setWarn] = useState({ userId: '', reason: '' });
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => { api.get('/registrar/students').then(r => setStudents(r.data)); }, []);
  useEffect(() => { load(); }, [load]);

  const issueWarn = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/registrar/warn', warn); setMsg({ ok: true, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const statusColor = s => s === 'Terminated' || s === 'Suspended' ? 'var(--danger)' : s === 'Graduated' ? 'var(--green)' : 'var(--text)';

  return (
    <div>
      <div className="page-header"><h1 className="page-title">All Students</h1></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Table
        headers={['ID', 'Name', 'GPA', 'Warnings', 'Honors', 'Status']}
        rows={students.map(s => [
          s.userId, s.name, s.gpa, `${s.warnings}/3`, s.honorCount,
          s.terminated ? 'Terminated' : s.graduated ? 'Graduated' : s.suspended ? 'Suspended' : 'Active'
        ])}
        colorFn={(val, ci) => ci === 5 ? statusColor(val) : ci === 2 ? (val >= 3.0 ? 'var(--green)' : val >= 2.0 ? 'var(--warning)' : 'var(--danger)') : null}
      />
      <div className="card" style={{ marginTop: 20 }}>
        <div className="section-title">Issue Warning</div>
        <form onSubmit={issueWarn}>
          <div className="grid-2 gap-12">
            <div className="form-group"><label className="form-label">User ID</label>
              <input className="form-input" placeholder="Student or Instructor ID" value={warn.userId} onChange={e => setWarn(w => ({ ...w, userId: e.target.value }))} required /></div>
            <div className="form-group"><label className="form-label">Reason</label>
              <input className="form-input" placeholder="Reason for warning" value={warn.reason} onChange={e => setWarn(w => ({ ...w, reason: e.target.value }))} required /></div>
          </div>
          <button className="btn btn-warning" type="submit">Issue Warning</button>
        </form>
      </div>
    </div>
  );
}

export function RegistrarActions() {
  const [tab, setTab] = useState('apps');
  const [apps, setApps] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [tabooWords, setTabooWords] = useState([]);
  const [tabooInput, setTabooInput] = useState('');
  const [cid, setCid] = useState('');
  const [justification, setJustification] = useState('');
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    api.get('/registrar/applications').then(r => setApps(r.data));
    api.get('/registrar/complaints').then(r => setComplaints(r.data));
    api.get('/registrar/reviews').then(r => setReviews(r.data));
    api.get('/registrar/taboo').then(r => setTabooWords(r.data));
  }, []);
  useEffect(() => { load(); }, [load]);

  const approveApp = async (appId) => {
    try { const r = await api.post('/registrar/approve-app', { appId, justification }); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Cannot approve.' }); }
  };
  const rejectApp = async (appId) => {
    try { await api.post('/registrar/reject-app', { appId }); setMsg({ ok: true, text: 'Application rejected.' }); load(); }
    catch { }
  };
  const resolveComplaint = async (action) => {
    if (!cid) { setMsg({ ok: false, text: 'Enter complaint ID.' }); return; }
    try { const r = await api.post('/registrar/resolve-complaint', { complaintId: cid, action }); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };
  const addTaboo = async () => {
    if (!tabooInput.trim()) return;
    try { const r = await api.post('/registrar/taboo', { word: tabooInput.trim() }); setTabooWords(r.data.tabooWords); setTabooInput(''); }
    catch { }
  };
  const removeTaboo = async (word) => {
    try { const r = await api.delete(`/registrar/taboo/${word}`); setTabooWords(r.data.tabooWords); }
    catch { }
  };

  return (
    <div>
      <div className="page-header"><h1 className="page-title">Applications, Complaints & Reviews</h1></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: 'apps',       label: '📋 Applications' },
        { id: 'complaints', label: '📣 Complaints' },
        { id: 'reviews',    label: '⭐ Reviews & Taboo' },
      ]} />

      {tab === 'apps' && (
        <>
          <Alert variant="info">Students must have GPA &gt; 3.0. If you approve below this threshold, provide a justification.</Alert>
          <div className="form-group" style={{ maxWidth: 400, marginBottom: 16 }}>
            <label className="form-label">Justification (if approving below-threshold student)</label>
            <input className="form-input" placeholder="Optional justification..." value={justification} onChange={e => setJustification(e.target.value)} />
          </div>
          <Table
            headers={['ID', 'Name', 'Role', 'GPA', 'Status', 'Actions']}
            rows={apps.filter(a => a.status === 'Pending').map(a => [
              a.appId, a.name, a.role, a.gpa.toFixed(2), a.status,
              <div key={a.appId} className="flex gap-8">
                <button className="btn btn-green btn-sm" onClick={() => approveApp(a.appId)}>Approve</button>
                <button className="btn btn-danger btn-sm" onClick={() => rejectApp(a.appId)}>Reject</button>
              </div>
            ])}
          />
        </>
      )}

      {tab === 'complaints' && (
        <>
          <Alert variant="warning">📌 Instructor complaints require mandatory action — you cannot dismiss them.</Alert>
          <Table
            headers={['ID', 'From', 'Against', 'Type', 'Description', 'Status']}
            rows={complaints.map(c => [
              c.complaintId, c.fromId, c.againstId,
              c.type === 'instructor_vs_student' ? '📌 Instructor' : 'Student',
              c.description.length > 50 ? c.description.slice(0,50)+'...' : c.description,
              c.resolved ? 'Resolved' : c.type === 'instructor_vs_student' ? '⚠️ Must Act' : 'Open'
            ])}
            colorFn={(val, ci) => {
              if (ci === 5) return val === '⚠️ Must Act' ? 'var(--danger)' : val === 'Resolved' ? 'var(--green)' : null;
              if (ci === 3 && val.includes('Instructor')) return 'var(--warning)';
              return null;
            }}
          />
          <div className="card" style={{ marginTop: 16 }}>
            <div className="section-title">Resolve Complaint</div>
            <div className="form-group" style={{ maxWidth: 300 }}>
              <label className="form-label">Complaint ID</label>
              <input className="form-input" placeholder="e.g. C001" value={cid} onChange={e => setCid(e.target.value)} />
            </div>
            <div className="flex gap-10" style={{ flexWrap: 'wrap' }}>
              <button className="btn btn-ghost" onClick={() => resolveComplaint('dismiss')}>Dismiss</button>
              <button className="btn btn-danger" onClick={() => resolveComplaint('punish')}>Punish Against-Party</button>
              <button className="btn btn-warning" onClick={() => resolveComplaint('warn_instructor')}>Warn Instructor (unjustified)</button>
            </div>
          </div>
        </>
      )}

      {tab === 'reviews' && (
        <>
          <Table
            headers={['Course', 'Student', 'Rating', 'Review', 'Status']}
            rows={reviews.map(r => [
              r.courseCode, r.studentId, `${r.rating} ★`,
              r.text.length > 60 ? r.text.slice(0,60)+'...' : r.text,
              r.flagged ? 'Flagged' : 'Visible'
            ])}
            colorFn={(val, ci) => ci === 4 ? (val === 'Flagged' ? 'var(--warning)' : 'var(--green)') : null}
          />
          <div className="card" style={{ marginTop: 20 }}>
            <div className="section-title">Taboo Word List</div>
            <div className="flex gap-8" style={{ flexWrap: 'wrap', marginBottom: 12 }}>
              {tabooWords.map(w => (
                <div key={w} style={{ background: '#FEF2F2', color: 'var(--danger)', border: '1px solid var(--danger)', borderRadius: 6, padding: '4px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                  {w}
                  <button onClick={() => removeTaboo(w)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)', fontWeight: 700 }}>×</button>
                </div>
              ))}
              {!tabooWords.length && <span style={{ color: 'var(--text3)', fontSize: 13 }}>No taboo words added yet.</span>}
            </div>
            <div className="flex gap-10" style={{ maxWidth: 360 }}>
              <input className="form-input" placeholder="Add taboo word..." value={tabooInput} onChange={e => setTabooInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && addTaboo()} />
              <button className="btn btn-green" onClick={addTaboo}>Add</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════
// AI PAGE
// ══════════════════════════════════════════════════
export function AIPage() {
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const ask = async e => {
    e.preventDefault(); if (!q.trim()) return;
    setLoading(true); setResult(null);
    try { const r = await api.post('/ai', { question: q }); setResult(r.data); }
    catch { setResult({ answer: 'Error contacting AI.', local: false }); }
    setLoading(false);
  };

  const suggestions = [
    'What are the graduation requirements?',
    'How does the warning system work?',
    'What are the semester phases?',
    'How do course reviews work?',
    'What is my current GPA?',
  ];

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="page-header">
        <h1 className="page-title">AI Assistant</h1>
        <p className="page-subtitle">Ask questions about College0 — answered from local knowledge, with LLM fallback.</p>
      </div>

      <div className="card">
        <form onSubmit={ask}>
          <div className="form-group">
            <label className="form-label">Your Question</label>
            <textarea className="form-input" rows={3} placeholder="e.g. What are the graduation requirements?" value={q} onChange={e => setQ(e.target.value)} />
          </div>
          <div className="flex gap-10">
            <button className="btn btn-primary" type="submit" disabled={loading}>{loading ? 'Thinking...' : 'Ask AI'}</button>
            <button className="btn btn-ghost" type="button" onClick={() => { setQ(''); setResult(null); }}>Clear</button>
          </div>
        </form>

        {!result && (
          <div style={{ marginTop: 16 }}>
            <div className="form-label" style={{ marginBottom: 8 }}>Quick Questions:</div>
            <div className="flex gap-8" style={{ flexWrap: 'wrap' }}>
              {suggestions.map(s => (
                <button key={s} className="btn btn-ghost btn-sm" onClick={() => setQ(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {loading && <div style={{ marginTop: 16 }}><Spinner /></div>}

        {result && (
          <div style={{ marginTop: 20 }}>
            <div className="form-label" style={{ marginBottom: 8 }}>Answer</div>
            <div className="card" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.6, margin: 0 }}>{result.answer}</pre>
            </div>
            <div className={`alert ${result.local ? 'alert-success' : 'alert-warning'}`} style={{ marginTop: 12 }}>
              {result.local
                ? '✅ Sourced from College0 local knowledge base.'
                : '⚠️ This answer is from a general AI model and may not reflect specific college policies.'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
