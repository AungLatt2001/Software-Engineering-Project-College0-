// client/src/pages/Pages.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth, api } from '../context/AuthContext';
import { StatCard, Badge, Alert, Spinner, Table, Tabs, Modal, InfoCard } from '../components/UI';

// ══════════════════════════════════════════════════
// HOME PAGE
// ══════════════════════════════════════════════════
export function HomePage({ onLogin }) {
  const [data, setData] = useState(null);
  const { user } = useAuth();
  useEffect(() => { api.get('/public').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <Spinner />;

  return (
    <div>
      <div className="hero-banner">
        <h1 className="hero-title">Welcome to College0</h1>
        <p className="hero-sub">An AI-enabled academic management portal for students, instructors, and administrators.</p>
        <div className="hero-chips">
          {[
            ['CURRENT PHASE', data.phaseLabel],
            ['SEMESTER', data.label || `#${data.semester}`],
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
          c.code, c.name, c.instructorName || c.instructorId || '—', c.timeSlot,
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

      {!user && (
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
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleLogin = async e => {
    e.preventDefault(); setErr(''); setLoading(true);
    try {
      const res = await login(form.userId, form.password);
      if (res.firstLogin) { setFirstLogin(true); }
      else { onSuccess(res.user, false); }
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
      onSuccess(u, true); // <- second arg: was first login, trigger tutorial
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
        <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 16 }}>You must change your default password before continuing. A short tutorial will follow.</p>
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
// TUTORIAL MODAL (spec: shown after a new user logs in for the first time)
// ══════════════════════════════════════════════════
const TUTORIAL_STEPS = {
  Student: [
    { title: 'Welcome to College0!', body: 'You have been admitted as a student. Here is a quick tour of what you can do.' },
    { title: '📊 Your Dashboard', body: 'Your dashboard shows your current GPA, warnings, enrolled courses, and academic standing. Honor roll badges appear here as you earn them.' },
    { title: '📚 My Courses', body: 'Register for 2–4 courses during the Registration phase. The system blocks time conflicts. If a class is full, you join the waitlist; the instructor admits people from the waitlist as space opens up.' },
    { title: '🎓 Transcript', body: 'View your grade history and cumulative GPA. Keep your GPA above 2.0 to avoid termination, and above 2.25 to avoid the registrar interview.' },
    { title: '⚙️ Reviews & More', body: 'During the Grading phase (before your grade is posted) you can submit anonymous course reviews. Reviews containing 1–2 taboo words are shown with asterisks and result in 1 warning; reviews with 3+ taboo words are hidden and result in 2 warnings. You can also apply for graduation and file complaints.' },
    { title: '👯 Study Buddy Matcher', body: 'Inside Reviews & More you can opt in to match with classmates in the same courses for collaborative studying — a College0 exclusive.' },
    { title: '🤖 AI Assistant', body: 'Ask the AI Assistant any question about College0 policies, your GPA, or what classes you are taking. It searches a local knowledge base first; if the answer is not found there, it can fall back to a general LLM (with a hallucination warning).' },
    { title: '⚠️ Warnings & Suspension', body: '3 warnings result in one-semester suspension and a $250 fine. Make sure to maintain good standing!' },
  ],
  Instructor: [
    { title: 'Welcome, Instructor!', body: 'You have been hired by College0. Here are your responsibilities.' },
    { title: '📊 Dashboard', body: 'See your assigned courses, enrolled students, and any waitlists at a glance.' },
    { title: '📚 My Classes', body: 'View each of your courses with full class roster. Admit students from the waitlist when seats open.' },
    { title: '✏️ Submit Grades', body: 'During the Grading phase, submit a final grade for every enrolled student. Forgetting to grade everyone results in a warning. Class averages above 3.5 or below 2.5 trigger registrar review.' },
    { title: '📣 Complaints', body: 'File complaints against students for misconduct. Note: complaints against students are taken seriously — the registrar must act, and unjustified complaints result in a warning to YOU.' },
    { title: '🤖 AI Assistant', body: 'Ask the AI about your students, class averages, or general College0 policies.' },
  ],
  Registrar: [
    { title: 'Registrar Tour', body: 'You administer College0. This is a quick walkthrough.' },
    { title: '📊 Overview', body: 'Advance the semester phase from here (SETUP → REGISTRATION → RUNNING → GRADING → CLOSED → next semester). Each transition triggers automatic rules per the College0 charter.' },
    { title: '📚 Manage Courses', body: 'Create courses, assign instructors, set capacities, and mark core courses.' },
    { title: '👤 All Students', body: 'View every student record. Issue warnings, clear interview holds, see who has unpaid fines.' },
    { title: '🎓 Faculty Review', body: 'Instructors with extreme class GPAs (>3.5 or <2.5) appear here for questioning. Clear, warn, or fire them.' },
    { title: '📋 Applications, Complaints & Reviews', body: 'Approve/reject applications (with justification when overriding rules), resolve complaints, moderate reviews, and manage the taboo word list.' },
  ],
};

export function TutorialModal({ role, onClose }) {
  const [step, setStep] = useState(0);
  const steps = TUTORIAL_STEPS[role] || TUTORIAL_STEPS.Student;
  const isLast = step === steps.length - 1;
  return (
    <Modal title={`Tutorial · Step ${step + 1} of ${steps.length}`} onClose={onClose}>
      <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--navy)', marginBottom: 12 }}>
        {steps[step].title}
      </h3>
      <p style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text2)', marginBottom: 24 }}>
        {steps[step].body}
      </p>
      <div className="flex items-center" style={{ justifyContent: 'space-between', gap: 12 }}>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setStep(s => Math.max(0, s - 1))}
          disabled={step === 0}
        >← Previous</button>
        <div style={{ display: 'flex', gap: 4 }}>
          {steps.map((_, i) => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: '50%',
              background: i === step ? 'var(--navy)' : 'var(--border)'
            }} />
          ))}
        </div>
        {isLast ? (
          <button className="btn btn-primary btn-sm" onClick={onClose}>Finish ✓</button>
        ) : (
          <button className="btn btn-primary btn-sm" onClick={() => setStep(s => s + 1)}>Next →</button>
        )}
      </div>
    </Modal>
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
        <Alert variant="info">Students with GPA &gt; 3.0 are admitted automatically subject to program quota. A registrar will review otherwise.</Alert>
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
export function StudentDashboard({ onShowTutorial }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState(null);
  const load = useCallback(() => {
    api.get('/student/me').then(r => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const payFine = async () => {
    setMsg(null);
    try { const r = await api.post('/student/pay-fine'); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!data) return <Spinner />;

  return (
    <div>
      <div className="hero-banner" style={{ marginBottom: 20 }}>
        <div className="flex items-center gap-12" style={{ marginBottom: 8, flexWrap: 'wrap' }}>
          <h1 className="hero-title" style={{ marginBottom: 0 }}>Welcome back, {data.name}</h1>
          {data.graduated && <span className="badge badge-green">GRADUATED 🎓</span>}
          {data.terminated && <span className="badge badge-danger">TERMINATED</span>}
          {data.suspended && <span className="badge badge-danger">SUSPENDED</span>}
          {data.interviewPending && <span className="badge badge-warning">INTERVIEW PENDING</span>}
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

      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}

      {/* Suspension + fine handling */}
      {data.suspended && data.fineDue > 0 && !data.finePaid && (
        <Alert variant="danger">
          <strong>⛔ You are suspended.</strong> A fine of <strong>${data.fineDue.toFixed(2)}</strong> must
          be paid before your suspension can be lifted at the next semester rollover.
          <div style={{ marginTop: 10 }}>
            <button className="btn btn-warning btn-sm" onClick={payFine}>💳 Pay ${data.fineDue.toFixed(2)} Fine</button>
          </div>
        </Alert>
      )}
      {data.suspended && data.finePaid && (
        <Alert variant="warning">
          ✅ Fine paid. Your suspension will be lifted at the start of semester {data.suspendedUntil}.
        </Alert>
      )}
      {data.interviewPending && (
        <Alert variant="warning">
          📅 Your GPA is in the 2.0–2.25 range. The registrar will schedule an interview with you.
        </Alert>
      )}

      {data.semestersCompleted <= 1 && !data.currentEnrollment?.length && !data.suspended && !data.terminated && (
        <Alert variant="info">
          👋 <strong>Welcome!</strong> Register for 2–4 courses during Registration phase · Maintain GPA &gt; 2.25 · Submit reviews during Grading phase (before grade is posted).{' '}
          {onShowTutorial && (
            <button className="btn btn-ghost btn-sm" onClick={onShowTutorial} style={{ marginLeft: 8 }}>
              📖 View Tutorial
            </button>
          )}
        </Alert>
      )}

      {data.warnings > 0 && data.warnings < 3 && (
        <Alert variant="warning">⚠️ You have {data.warnings} warning(s). 3 warnings result in suspension and a $250 fine.</Alert>
      )}

      <div style={{ marginTop: 24 }}>
        <button className="btn btn-ghost btn-sm" onClick={onShowTutorial}>📖 Replay Tutorial</button>
      </div>
    </div>
  );
}

export function StudentCourses() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState(null);

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
          rows={data.enrolled.map(c => [c.code, c.name, c.timeSlot, c.instructorName || c.instructorId || '—',
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
          <Alert variant="info">
            ⏰ Time conflicts and missing prerequisites are blocked automatically.
            Prerequisites must be completed with at least a C grade.
          </Alert>
          <Table
            headers={['Code', 'Name', 'Time Slot', 'Seats', 'Core', 'Prerequisites', '']}
            rows={data.available.map(c => [
              c.code, c.name, c.timeSlot,
              c.enrolled.length >= c.capacity ? 'FULL' : `${c.capacity - c.enrolled.length} left`,
              c.isCore ? '★' : '',
              (c.prerequisites && c.prerequisites.length)
                ? c.prerequisites.join(', ')
                : '—',
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
        <StatCard label="Cumulative GPA" value={data.gpa}
          sub={data.gpa >= 3.0 ? 'Good Standing' : data.gpa >= 2.0 ? 'Standing' : 'Below 2.0 — at risk'}
          variant={data.gpa >= 3.0 ? 'green' : data.gpa >= 2.0 ? 'warn' : 'danger'} />
        <StatCard label="Warnings"        value={`${data.warnings}/3`}      variant={data.warnings >= 2 ? 'danger' : 'navy'} />
        <StatCard label="Honor Roll"      value={data.honorCount}           variant="navy" />
      </div>
      <div className="section-title">Grade History</div>
      {data.grades?.length ? (
        <Table
          headers={['Code', 'Course', 'Grade', 'Semester']}
          rows={data.grades.map(g => [
            g.courseCode, g.courseName, g.grade || '—',
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

  const load = useCallback(() => {
    api.get('/student/courses').then(r => setCourses(r.data.enrolled || []));
    api.get('/student/me').then(r => setMe(r.data));
  }, []);
  useEffect(() => { load(); }, [load]);

  const submitReview = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/student/review', review); setMsg({ ok: r.data.ok, text: r.data.msg }); setReview(v => ({ ...v, text: '' })); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const submitGraduation = async () => {
    setMsg(null);
    try { const r = await api.post('/student/graduate'); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const submitComplaint = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/student/complaint', complaint); setMsg({ ok: true, text: `Complaint ${r.data.complaintId} filed.` }); setComplaint({ againstId: '', description: '' }); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!me) return <Spinner />;
  const total = new Set(me.completedCourses || []).size;
  const coreRequired = ['CSC 10100','CSC 10200','CSC 21700','CSC 22000'];
  const coreDone = coreRequired.filter(c => (me.completedCourses || []).includes(c)).length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Reviews, Graduation & More</h1>
      </div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: 'review',      label: '✍️ Write Review' },
        { id: 'browse',      label: '📖 Read Reviews' },
        { id: 'graduation',  label: '🎓 Graduation' },
        { id: 'complaint',   label: '📣 Complaint' },
        { id: 'buddy',       label: '👯 Study Buddy' },
      ]} />

      {tab === 'review' && (
        <div className="card">
          <div className="section-title">Submit a Course Review</div>
          <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 8 }}>Reviews are anonymous. Only available during Grading period, before your grade is posted.</p>
          <Alert variant="info">
            <strong>Taboo word policy:</strong> reviews with 1–2 taboo words are shown publicly with those words replaced by asterisks (1 warning issued). Reviews with 3+ taboo words are hidden entirely (2 warnings issued).
          </Alert>
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

      {tab === 'browse' && <ReadReviewsTab />}

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

      {tab === 'buddy' && <StudyBuddyTab />}
    </div>
  );
}

// ── Read Reviews sub-tab ─────────────────────────────────────────────────

function ReadReviewsTab() {
  const [courses, setCourses] = useState([]);
  const [selected, setSelected] = useState('');
  const [reviews, setReviews] = useState(null);

  useEffect(() => {
    api.get('/public').then(r => setCourses(r.data.courses || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) { setReviews(null); return; }
    api.get(`/public/course-reviews/${encodeURIComponent(selected)}`)
      .then(r => setReviews(r.data))
      .catch(() => setReviews({ reviews: [], count: 0 }));
  }, [selected]);

  return (
    <div className="card">
      <div className="section-title">Read Course Reviews</div>
      <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 12 }}>
        Browse anonymous reviews for any course in the catalogue. Reviews with 3+ taboo words are hidden; reviews with 1–2 taboo words have those words masked with asterisks.
      </p>
      <div className="form-group">
        <label className="form-label">Course</label>
        <select className="form-input" value={selected} onChange={e => setSelected(e.target.value)}>
          <option value="">Select a course to view its reviews...</option>
          {courses.map(c => <option key={c.code} value={c.code}>{c.code} — {c.name}</option>)}
        </select>
      </div>
      {reviews && (
        <div style={{ marginTop: 16 }}>
          {reviews.averageRating != null && (
            <div style={{ marginBottom: 12, fontSize: 14, color: 'var(--text2)' }}>
              <strong>{reviews.count}</strong> review(s) · Average rating: <strong>{reviews.averageRating} ★</strong>
            </div>
          )}
          {reviews.count === 0 ? (
            <div className="empty-state">No reviews yet for this course.</div>
          ) : reviews.reviews.map((r, i) => (
            <div key={i} style={{
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 8, padding: 14, marginBottom: 10,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <div style={{ color: 'var(--navy)', fontWeight: 600 }}>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</div>
                {r.tabooCount > 0 && (
                  <Badge variant="warning">{r.tabooCount} word(s) masked</Badge>
                )}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text)', whiteSpace: 'pre-wrap' }}>{r.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Study Buddy sub-tab (creative feature) ────────────────────────────────

function StudyBuddyTab() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ bio: '', availability: '' });
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    api.get('/student/study-buddy').then(r => {
      setData(r.data);
      setForm({ bio: r.data.bio || '', availability: r.data.availability || '' });
    }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const optIn = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/student/study-buddy', form); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const optOut = async () => {
    setMsg(null);
    try { const r = await api.delete('/student/study-buddy'); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  if (!data) return <Spinner />;

  return (
    <div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <div className="card">
        <div className="section-title">👯 Study Buddy Matcher</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 12 }}>
          Opt in to be matched with classmates in the same courses. The system ranks matches by shared courses (10 pts each) and shared availability tokens (2 pts each). Your bio is visible only to other opted-in students.
        </p>
        <form onSubmit={optIn}>
          <div className="form-group">
            <label className="form-label">Short Bio</label>
            <textarea className="form-input" placeholder="Tell potential buddies a bit about you and how you like to study..."
              value={form.bio} onChange={e => setForm(f => ({ ...f, bio: e.target.value }))} maxLength={500} />
          </div>
          <div className="form-group">
            <label className="form-label">Availability</label>
            <input className="form-input" placeholder="e.g. evenings weekends mornings"
              value={form.availability} onChange={e => setForm(f => ({ ...f, availability: e.target.value }))} maxLength={200} />
          </div>
          <div className="flex gap-10">
            <button className="btn btn-primary" type="submit">{data.optedIn ? 'Update Profile' : 'Opt In'}</button>
            {data.optedIn && (
              <button className="btn btn-danger" type="button" onClick={optOut}>Opt Out</button>
            )}
          </div>
        </form>
      </div>

      {data.optedIn && (
        <div style={{ marginTop: 20 }}>
          <div className="section-title">Your Matches ({data.matches.length})</div>
          {!data.courses.length ? (
            <Alert variant="info">Register for courses first — matches are based on shared courses.</Alert>
          ) : data.matches.length === 0 ? (
            <div className="empty-state">No matches yet. Check back as more classmates opt in.</div>
          ) : (
            data.matches.map(m => (
              <div key={m.userId} className="card" style={{ marginBottom: 10, borderLeft: '3px solid var(--green)' }}>
                <div className="flex items-center gap-12" style={{ marginBottom: 6, flexWrap: 'wrap' }}>
                  <strong style={{ color: 'var(--navy)' }}>{m.name}</strong>
                  <span style={{ fontSize: 12, color: 'var(--text3)' }}>{m.userId}</span>
                  <Badge variant="green">Score {m.score}</Badge>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 6 }}>
                  <strong>Shared courses:</strong> {m.sharedCourses.join(', ')}
                </div>
                {m.sharedAvailability.length > 0 && (
                  <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 6 }}>
                    <strong>Both available:</strong> {m.sharedAvailability.join(', ')}
                  </div>
                )}
                {m.bio && (
                  <div style={{ fontSize: 13, color: 'var(--text)', marginTop: 6, fontStyle: 'italic' }}>
                    "{m.bio}"
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════
// INSTRUCTOR PAGES
// ══════════════════════════════════════════════════
export function InstructorDashboard({ onShowTutorial }) {
  const [data, setData] = useState(null);
  useEffect(() => { api.get('/instructor/me').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <Spinner />;
  const { instructor: inst, courses } = data;

  return (
    <div>
      <div className="hero-banner" style={{ marginBottom: 20 }}>
        <h1 className="hero-title">Welcome, {inst.name}</h1>
        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>
          {inst.userId} ·{' '}
          {inst.fired ? '🚫 Removed' :
           inst.suspended ? '⛔ Suspended' :
           inst.reviewPending ? '🔍 Under Review' : '✅ Active Instructor'}
        </p>
        <div className="hero-chips" style={{ marginTop: 20 }}>
          <div className="hero-chip"><div className="hero-chip-label">ACTIVE COURSES</div><div className="hero-chip-value">{courses.length}</div></div>
          <div className="hero-chip"><div className="hero-chip-label">TOTAL STUDENTS</div><div className="hero-chip-value">{courses.reduce((s,c) => s + c.enrolled.length, 0)}</div></div>
          <div className="hero-chip"><div className="hero-chip-label">WARNINGS</div><div className="hero-chip-value">{inst.warnings}/3</div></div>
        </div>
      </div>

      {inst.reviewPending && (
        <Alert variant="warning">
          🔍 The registrar has flagged you for review (extreme class GPA). You will be questioned about your grading.
        </Alert>
      )}

      <div className="section-title">My Assigned Courses</div>
      {courses.map(c => (
        <div key={c.code} className="card" style={{ marginBottom: 12, borderLeft: '3px solid var(--navy)' }}>
          <div className="flex items-center gap-16" style={{ flexWrap: 'wrap' }}>
            <strong>{c.code}</strong>
            <span style={{ color: 'var(--text2)' }}>{c.name}</span>
            <span style={{ color: 'var(--text3)', fontSize: 12 }}>{c.timeSlot}</span>
            <span style={{ color: 'var(--navy)', fontSize: 13, marginLeft: 'auto' }}>{c.enrolled.length}/{c.capacity} students</span>
            {c.waitlist.length > 0 && <Badge variant="warning">+{c.waitlist.length} waitlist</Badge>}
            {c.cancelled && <Badge variant="danger">CANCELLED</Badge>}
          </div>
        </div>
      ))}

      <div style={{ marginTop: 24 }}>
        <button className="btn btn-ghost btn-sm" onClick={onShowTutorial}>📖 Replay Tutorial</button>
      </div>
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
          <div className="flex items-center gap-12" style={{ marginBottom: 10, flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--navy)' }}>{c.code} — {c.name}</h3>
            <span style={{ fontSize: 12, color: 'var(--text3)' }}>[{c.timeSlot}]</span>
            {c.cancelled && <Badge variant="danger">CANCELLED</Badge>}
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
      <Alert variant="info">
        💡 Remember to grade <strong>every</strong> enrolled student. Skipping students results in a warning at phase close. Class averages above 3.5 or below 2.5 trigger registrar review.
      </Alert>
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
  const [actions, setActions] = useState([]);
  const [quotaInput, setQuotaInput] = useState('');
  const [semList, setSemList] = useState([]);

  const load = useCallback(() => {
    api.get('/registrar/overview').then(r => setData(r.data)).catch(() => {});
    api.get('/registrar/semesters').then(r => setSemList(r.data.semesters || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const advance = async () => {
    setActions([]);
    try {
      const r = await api.post('/registrar/advance-phase');
      setMsg({ ok: true, text: r.data.msg });
      setActions(r.data.actions || []);
      load();
    }
    catch (e) { setMsg({ ok: false, text: 'Error advancing phase.' }); }
  };
  const closeSpecialReg = async () => {
    try { await api.post('/registrar/close-special-reg'); setMsg({ ok: true, text: 'Special registration closed.' }); load(); }
    catch { }
  };
  const setQuota = async () => {
    const q = parseInt(quotaInput);
    if (!q || q < 1) { setMsg({ ok: false, text: 'Quota must be ≥ 1.' }); return; }
    try { const r = await api.post('/registrar/program-quota', { quota: q }); setMsg({ ok: r.data.ok, text: r.data.msg }); setQuotaInput(''); load(); }
    catch { setMsg({ ok: false, text: 'Error setting quota.' }); }
  };
  const jumpSemester = async (sem) => {
    if (!sem) return;
    setActions([]);
    try {
      const r = await api.post('/registrar/jump-semester', { semester: parseInt(sem) });
      setMsg({ ok: r.data.ok, text: r.data.msg });
      load();
    } catch { setMsg({ ok: false, text: 'Could not switch semester.' }); }
  };

  if (!data) return <Spinner />;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Registrar Overview</h1>
        <p className="page-subtitle">Full administrative access to all system operations.</p>
      </div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}

      <div className="card" style={{ borderLeft: '4px solid var(--navy)', marginBottom: 20 }}>
        <div className="flex items-center gap-16" style={{ flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--navy)' }}>
              {data.label || `Semester ${data.semester}`} · {data.phaseLabel}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)' }}>
              Internal sequence #{data.semester}
            </div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: 'var(--text2)', display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 2 }}>Switch Semester</span>
              <select
                className="form-input"
                style={{ padding: '6px 10px', fontSize: 13, minWidth: 160 }}
                value={data.semester}
                onChange={e => jumpSemester(e.target.value)}
              >
                {semList.map(s => (
                  <option key={s.semester} value={s.semester}>
                    {s.label}{s.isCurrent ? ' (current)' : ''}
                  </option>
                ))}
              </select>
            </label>
            {data.specialRegistration && (
              <button className="btn btn-warning" onClick={closeSpecialReg}>Close Special Registration</button>
            )}
            <button className="btn btn-primary" onClick={advance}>Advance Phase →</button>
          </div>
        </div>
      </div>

      {data.specialRegistration && <Alert variant="warning">⚡ Special registration period is currently open.</Alert>}

      {actions.length > 0 && (
        <div className="card" style={{ marginBottom: 20, borderLeft: '3px solid var(--green)' }}>
          <div className="section-title">📋 Automatic Actions Taken</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
            {actions.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </div>
      )}

      <div className="grid-4 gap-16" style={{ marginBottom: 24 }}>
        <StatCard label="Active Students"      value={data.studentCount}    variant="navy" />
        <StatCard label="Pending Applications" value={data.pendingApps}     variant={data.pendingApps > 0 ? 'warn' : 'navy'} />
        <StatCard label="Open Complaints"      value={data.openComplaints}  variant={data.openComplaints > 0 ? 'danger' : 'navy'} />
        <StatCard label="Active Courses"       value={data.activeCourses}   variant="green" />
      </div>

      <div className="grid-3 gap-16" style={{ marginBottom: 24 }}>
        <StatCard label="Faculty to Question"  value={data.instructorsToReview}
          sub={data.instructorsToReview > 0 ? 'Visit Faculty Review' : 'None pending'}
          variant={data.instructorsToReview > 0 ? 'danger' : 'navy'} />
        <StatCard label="Pending Interviews"   value={data.interviewPending}
          sub={data.interviewPending > 0 ? 'See All Students' : 'None pending'}
          variant={data.interviewPending > 0 ? 'warn' : 'navy'} />
        <StatCard label="Program Quota"        value={data.programQuota}
          sub={`${data.studentCount}/${data.programQuota} students`}
          variant={data.studentCount >= data.programQuota ? 'danger' : 'navy'} />
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="section-title">Set Program Quota</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 10 }}>
          Maximum number of active students. Approving applicants beyond this requires justification.
        </p>
        <div className="flex gap-10" style={{ maxWidth: 360 }}>
          <input className="form-input" type="number" min="1" placeholder={`Current: ${data.programQuota}`}
            value={quotaInput} onChange={e => setQuotaInput(e.target.value)} />
          <button className="btn btn-primary" onClick={setQuota}>Update</button>
        </div>
      </div>
    </div>
  );
}

export function RegistrarCourses() {
  const [courses, setCourses] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [form, setForm] = useState({ code: '', name: '', instructorId: '', timeSlot: '', capacity: 20, isCore: false, prerequisites: '' });
  const [msg, setMsg] = useState(null);
  const [editing, setEditing] = useState(null);   // course object currently being edited
  const [confirmDel, setConfirmDel] = useState(null);

  const load = useCallback(() => {
    api.get('/registrar/courses').then(r => setCourses(r.data));
    api.get('/registrar/instructors').then(r => setInstructors(r.data));
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async e => {
    e.preventDefault(); setMsg(null);
    try {
      const payload = { ...form,
        prerequisites: form.prerequisites
          .split(',').map(s => s.trim()).filter(Boolean) };
      const r = await api.post('/registrar/create-course', payload);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      if (r.data.ok) setForm({ code: '', name: '', instructorId: '', timeSlot: '', capacity: 20, isCore: false, prerequisites: '' });
      load();
    }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const startEdit = c => setEditing({
    code:         c.code,
    name:         c.name,
    instructorId: c.instructorId || '',
    timeSlot:     c.timeSlot,
    capacity:     c.capacity,
    isCore:       !!c.isCore,
    cancelled:    !!c.cancelled,
    prerequisites: (c.prerequisites || []).join(', '),
  });

  const saveEdit = async () => {
    setMsg(null);
    try {
      const payload = { ...editing,
        prerequisites: editing.prerequisites
          .split(',').map(s => s.trim()).filter(Boolean) };
      const r = await api.post('/registrar/update-course', payload);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      if (r.data.ok) setEditing(null);
      load();
    } catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const remove = async code => {
    try {
      const r = await api.delete(`/registrar/delete-course/${encodeURIComponent(code)}`);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      setConfirmDel(null);
      load();
    } catch (e) { setMsg({ ok: false, text: 'Error deleting course.' }); }
  };

  // Only show eligible (not suspended/fired) instructors in the assign dropdown.
  const eligibleInstructors = instructors.filter(i => !i.suspended && !i.fired);

  return (
    <div>
      <div className="page-header"><h1 className="page-title">Manage Courses</h1></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Table
        headers={['Code', 'Name', 'Instructor', 'Time', 'Enrolled', 'Core', 'Prereqs', 'Rating', 'Status', '']}
        rows={courses.map(c => [
          c.code, c.name, c.instructorName || c.instructorId || '⚠ Unassigned', c.timeSlot,
          `${c.enrolled.length}/${c.capacity}`,
          c.isCore ? '★' : '',
          (c.prerequisites && c.prerequisites.length) ? c.prerequisites.join(', ') : '—',
          c.rating ? `${c.rating} ★` : '—',
          c.cancelled ? 'Cancelled' : 'Active',
          <div key={c.code} className="flex gap-8">
            <button className="btn btn-ghost btn-sm" onClick={() => startEdit(c)}>Edit</button>
            <button className="btn btn-danger btn-sm" onClick={() => setConfirmDel(c.code)}>Delete</button>
          </div>
        ])}
        colorFn={(val, ci) => {
          if (ci === 8) return val === 'Cancelled' ? 'var(--danger)' : 'var(--green)';
          if (ci === 2 && String(val).includes('Unassigned')) return 'var(--warning)';
          return null;
        }}
      />

      {editing && (
        <Modal title={`Edit ${editing.code}`} onClose={() => setEditing(null)}>
          <div className="form-group"><label className="form-label">Name</label>
            <input className="form-input" value={editing.name} onChange={e => setEditing(p => ({ ...p, name: e.target.value }))} /></div>
          <div className="form-group"><label className="form-label">Instructor</label>
            <select className="form-input" value={editing.instructorId} onChange={e => setEditing(p => ({ ...p, instructorId: e.target.value }))}>
              <option value="">⚠ Unassigned</option>
              {eligibleInstructors.map(i => <option key={i.userId} value={i.userId}>{i.userId} — {i.name}</option>)}
            </select></div>
          <div className="form-group"><label className="form-label">Time Slot</label>
            <input className="form-input" value={editing.timeSlot} onChange={e => setEditing(p => ({ ...p, timeSlot: e.target.value }))} /></div>
          <div className="grid-2 gap-12">
            <div className="form-group"><label className="form-label">Capacity</label>
              <input className="form-input" type="number" min="3" max="60" value={editing.capacity} onChange={e => setEditing(p => ({ ...p, capacity: parseInt(e.target.value) || 0 }))} /></div>
            <div className="form-group"><label className="form-label">Core Course</label>
              <select className="form-input" value={editing.isCore} onChange={e => setEditing(p => ({ ...p, isCore: e.target.value === 'true' }))}>
                <option value="false">No</option><option value="true">Yes ★</option>
              </select></div>
          </div>
          <div className="form-group"><label className="form-label">Prerequisites (comma-separated codes)</label>
            <input className="form-input" placeholder="e.g. CSC 10100, CSC 10200" value={editing.prerequisites} onChange={e => setEditing(p => ({ ...p, prerequisites: e.target.value }))} /></div>
          <div className="form-group"><label className="form-label">Status</label>
            <select className="form-input" value={editing.cancelled} onChange={e => setEditing(p => ({ ...p, cancelled: e.target.value === 'true' }))}>
              <option value="false">Active</option><option value="true">Cancelled</option>
            </select></div>
          <div className="flex gap-10" style={{ marginTop: 8 }}>
            <button className="btn btn-primary" onClick={saveEdit}>Save Changes</button>
            <button className="btn btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </Modal>
      )}

      {confirmDel && (
        <Modal title={`Delete ${confirmDel}?`} onClose={() => setConfirmDel(null)}>
          <Alert variant="danger">
            This permanently deletes the course and all its enrollments, waitlist entries, and reviews.
            Other courses with this as a prerequisite will have it removed from their prereq list.
            This cannot be undone.
          </Alert>
          <div className="flex gap-10" style={{ marginTop: 12 }}>
            <button className="btn btn-danger" onClick={() => remove(confirmDel)}>Delete Permanently</button>
            <button className="btn btn-ghost" onClick={() => setConfirmDel(null)}>Cancel</button>
          </div>
        </Modal>
      )}

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
                {eligibleInstructors.map(i => <option key={i.userId} value={i.userId}>{i.userId} — {i.name}</option>)}
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
          <div className="form-group">
            <label className="form-label">Prerequisites (comma-separated codes, optional)</label>
            <input className="form-input" placeholder="e.g. CSC 10100, CSC 10200"
              value={form.prerequisites} onChange={e => setForm(f => ({ ...f, prerequisites: e.target.value }))} />
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
  const [editing, setEditing] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null);

  const load = useCallback(() => { api.get('/registrar/students').then(r => setStudents(r.data)); }, []);
  useEffect(() => { load(); }, [load]);

  const issueWarn = async e => {
    e.preventDefault(); setMsg(null);
    try { const r = await api.post('/registrar/warn', warn); setMsg({ ok: true, text: r.data.msg }); setWarn({ userId: '', reason: '' }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };
  const clearInterview = async uid => {
    try { const r = await api.post(`/registrar/clear-interview/${uid}`); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: 'Error' }); }
  };

  const startEdit = s => setEditing({
    userId:           s.userId,
    name:             s.name,
    gpa:              s.gpa,
    warnings:         s.warnings,
    honorCount:       s.honorCount,
    suspended:        s.suspended,
    terminated:       s.terminated,
    graduated:        s.graduated,
    interviewPending: s.interviewPending,
    fineDue:          s.fineDue,
    finePaid:         s.finePaid,
  });

  const saveEdit = async () => {
    setMsg(null);
    try {
      const r = await api.post('/registrar/update-student', editing);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      if (r.data.ok) setEditing(null);
      load();
    } catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const remove = async uid => {
    try {
      const r = await api.delete(`/registrar/delete-student/${uid}`);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      setConfirmDel(null);
      load();
    } catch (e) { setMsg({ ok: false, text: 'Error deleting student.' }); }
  };

  const statusOf = s => s.terminated ? 'Terminated' : s.graduated ? 'Graduated' : s.suspended ? 'Suspended' : 'Active';
  const statusColor = s => s === 'Terminated' || s === 'Suspended' ? 'var(--danger)' : s === 'Graduated' ? 'var(--green)' : 'var(--text)';

  return (
    <div>
      <div className="page-header"><h1 className="page-title">Manage Students</h1></div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      <Table
        headers={['ID', 'Name', 'GPA', 'Warnings', 'Honors', 'Status', 'Flags', 'Actions']}
        rows={students.map(s => {
          const flags = [];
          if (s.interviewPending) flags.push('📅 Interview');
          if (s.fineDue > 0 && !s.finePaid) flags.push(`💰 $${s.fineDue}`);
          if (s.fineDue > 0 && s.finePaid) flags.push('✅ Fine paid');
          return [
            s.userId, s.name, s.gpa, `${s.warnings}/3`, s.honorCount, statusOf(s),
            flags.join(', ') || '—',
            <div key={s.userId} className="flex gap-8" style={{ flexWrap: 'wrap' }}>
              <button className="btn btn-ghost btn-sm" onClick={() => startEdit(s)}>Edit</button>
              <button className="btn btn-danger btn-sm" onClick={() => setConfirmDel(s.userId)}>Delete</button>
              {s.interviewPending && (
                <button className="btn btn-warning btn-sm" onClick={() => clearInterview(s.userId)}>Clear Interview</button>
              )}
            </div>,
          ];
        })}
        colorFn={(val, ci) => ci === 5 ? statusColor(val) : ci === 2 ? (val >= 3.0 ? 'var(--green)' : val >= 2.0 ? 'var(--warning)' : 'var(--danger)') : null}
      />

      {editing && (
        <Modal title={`Edit ${editing.userId}`} onClose={() => setEditing(null)}>
          <div className="form-group"><label className="form-label">Name</label>
            <input className="form-input" value={editing.name} onChange={e => setEditing(p => ({ ...p, name: e.target.value }))} /></div>
          <div className="grid-2 gap-12">
            <div className="form-group"><label className="form-label">GPA (0–4)</label>
              <input className="form-input" type="number" step="0.01" min="0" max="4" value={editing.gpa} onChange={e => setEditing(p => ({ ...p, gpa: parseFloat(e.target.value) || 0 }))} /></div>
            <div className="form-group"><label className="form-label">Warnings</label>
              <input className="form-input" type="number" min="0" max="3" value={editing.warnings} onChange={e => setEditing(p => ({ ...p, warnings: parseInt(e.target.value) || 0 }))} /></div>
            <div className="form-group"><label className="form-label">Honor Count</label>
              <input className="form-input" type="number" min="0" value={editing.honorCount} onChange={e => setEditing(p => ({ ...p, honorCount: parseInt(e.target.value) || 0 }))} /></div>
            <div className="form-group"><label className="form-label">Fine Due ($)</label>
              <input className="form-input" type="number" step="0.01" min="0" value={editing.fineDue} onChange={e => setEditing(p => ({ ...p, fineDue: parseFloat(e.target.value) || 0 }))} /></div>
          </div>
          <div className="grid-2 gap-12">
            {[
              ['Suspended',  'suspended'],
              ['Terminated', 'terminated'],
              ['Graduated',  'graduated'],
              ['Interview Pending', 'interviewPending'],
              ['Fine Paid',  'finePaid'],
            ].map(([label, key]) => (
              <div className="form-group" key={key}>
                <label className="form-label">{label}</label>
                <select className="form-input" value={editing[key]} onChange={e => setEditing(p => ({ ...p, [key]: e.target.value === 'true' }))}>
                  <option value="false">No</option><option value="true">Yes</option>
                </select>
              </div>
            ))}
          </div>
          <div className="flex gap-10" style={{ marginTop: 8 }}>
            <button className="btn btn-primary" onClick={saveEdit}>Save Changes</button>
            <button className="btn btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </Modal>
      )}

      {confirmDel && (
        <Modal title={`Delete ${confirmDel}?`} onClose={() => setConfirmDel(null)}>
          <Alert variant="danger">
            This permanently deletes the student and all their enrollments, reviews, complaints, and warnings.
            This cannot be undone.
          </Alert>
          <div className="flex gap-10" style={{ marginTop: 12 }}>
            <button className="btn btn-danger" onClick={() => remove(confirmDel)}>Delete Permanently</button>
            <button className="btn btn-ghost" onClick={() => setConfirmDel(null)}>Cancel</button>
          </div>
        </Modal>
      )}

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

// ── Registrar: Manage Instructors (full CRUD — issue 6) ───────────────────

export function RegistrarInstructors() {
  const [list, setList] = useState([]);
  const [msg, setMsg] = useState(null);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', email: '' });
  const [editing, setEditing] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null);

  const load = useCallback(() => {
    api.get('/registrar/instructors').then(r => setList(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async e => {
    e.preventDefault(); setMsg(null);
    try {
      const r = await api.post('/registrar/create-instructor', createForm);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      if (r.data.ok) { setCreating(false); setCreateForm({ name: '', email: '' }); }
      load();
    } catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const startEdit = async i => {
    try {
      const r = await api.get(`/registrar/instructor/${i.userId}`);
      setEditing({
        userId:        r.data.userId,
        name:          r.data.name,
        email:         r.data.email,
        warnings:      r.data.warnings,
        suspended:     r.data.suspended,
        fired:         r.data.fired,
        reviewPending: r.data.reviewPending,
        courses:       r.data.courses,
      });
    } catch { setMsg({ ok: false, text: 'Could not load instructor.' }); }
  };

  const saveEdit = async () => {
    setMsg(null);
    try {
      const { courses, ...payload } = editing;
      const r = await api.post('/registrar/update-instructor', payload);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      if (r.data.ok) setEditing(null);
      load();
    } catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  const remove = async uid => {
    try {
      const r = await api.delete(`/registrar/delete-instructor/${uid}`);
      setMsg({ ok: r.data.ok, text: r.data.msg });
      setConfirmDel(null);
      load();
    } catch (e) { setMsg({ ok: false, text: 'Error deleting instructor.' }); }
  };

  const statusOf = i => i.fired ? 'Removed' : i.suspended ? 'Suspended' : i.reviewPending ? 'Under Review' : 'Active';
  const statusColor = s => s === 'Removed' || s === 'Suspended' ? 'var(--danger)' :
                           s === 'Under Review' ? 'var(--warning)' : 'var(--green)';

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Manage Instructors</h1>
        <p className="page-subtitle">Hire, edit, or remove instructors. Firing automatically unassigns their courses (via database trigger).</p>
      </div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <button className="btn btn-green" onClick={() => setCreating(true)}>+ Hire New Instructor</button>
      </div>

      <Table
        headers={['ID', 'Name', 'Warnings', 'Status', 'Actions']}
        rows={list.map(i => [
          i.userId, i.name, `${i.warnings}/3`, statusOf(i),
          <div key={i.userId} className="flex gap-8" style={{ flexWrap: 'wrap' }}>
            <button className="btn btn-ghost btn-sm" onClick={() => startEdit(i)}>Edit</button>
            <button className="btn btn-danger btn-sm" onClick={() => setConfirmDel(i.userId)}>Delete</button>
          </div>
        ])}
        colorFn={(val, ci) => ci === 3 ? statusColor(val) : null}
      />

      {creating && (
        <Modal title="Hire New Instructor" onClose={() => setCreating(false)}>
          <form onSubmit={create}>
            <div className="form-group"><label className="form-label">Full Name</label>
              <input className="form-input" autoFocus placeholder="e.g. Donald Knuth"
                value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))} required /></div>
            <div className="form-group"><label className="form-label">Email</label>
              <input className="form-input" type="email" placeholder="email@college0.edu"
                value={createForm.email} onChange={e => setCreateForm(f => ({ ...f, email: e.target.value }))} required /></div>
            <Alert variant="info">
              A user ID (I##) and default password (<code>pass123</code>) will be auto-assigned. The new instructor must change the password at first login.
            </Alert>
            <div className="flex gap-10" style={{ marginTop: 12 }}>
              <button className="btn btn-primary" type="submit">Create Instructor</button>
              <button className="btn btn-ghost" type="button" onClick={() => setCreating(false)}>Cancel</button>
            </div>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit ${editing.userId}`} onClose={() => setEditing(null)}>
          <div className="form-group"><label className="form-label">Name</label>
            <input className="form-input" value={editing.name} onChange={e => setEditing(p => ({ ...p, name: e.target.value }))} /></div>
          <div className="form-group"><label className="form-label">Email</label>
            <input className="form-input" type="email" value={editing.email} onChange={e => setEditing(p => ({ ...p, email: e.target.value }))} /></div>
          <div className="grid-2 gap-12">
            <div className="form-group"><label className="form-label">Warnings</label>
              <input className="form-input" type="number" min="0" max="3"
                value={editing.warnings} onChange={e => setEditing(p => ({ ...p, warnings: parseInt(e.target.value) || 0 }))} /></div>
            <div className="form-group"><label className="form-label">Suspended</label>
              <select className="form-input" value={editing.suspended} onChange={e => setEditing(p => ({ ...p, suspended: e.target.value === 'true' }))}>
                <option value="false">No</option><option value="true">Yes</option>
              </select></div>
            <div className="form-group"><label className="form-label">Fired</label>
              <select className="form-input" value={editing.fired} onChange={e => setEditing(p => ({ ...p, fired: e.target.value === 'true' }))}>
                <option value="false">No</option><option value="true">Yes (will unassign courses)</option>
              </select></div>
            <div className="form-group"><label className="form-label">Review Pending</label>
              <select className="form-input" value={editing.reviewPending} onChange={e => setEditing(p => ({ ...p, reviewPending: e.target.value === 'true' }))}>
                <option value="false">No</option><option value="true">Yes</option>
              </select></div>
          </div>
          {editing.courses && editing.courses.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="form-label">Currently Teaching</div>
              <div style={{ fontSize: 12, color: 'var(--text2)', padding: '6px 0' }}>
                {editing.courses.map(c => `${c.code} (${c.timeSlot})`).join(' · ')}
              </div>
            </div>
          )}
          <div className="flex gap-10" style={{ marginTop: 8 }}>
            <button className="btn btn-primary" onClick={saveEdit}>Save Changes</button>
            <button className="btn btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </Modal>
      )}

      {confirmDel && (
        <Modal title={`Delete ${confirmDel}?`} onClose={() => setConfirmDel(null)}>
          <Alert variant="danger">
            This permanently deletes the instructor. Their courses will be left unassigned (instructor_id = NULL).
            The deletion is wrapped in <code>PRAGMA foreign_keys = OFF/ON</code> to mirror the MySQL <code>SET FOREIGN_KEY_CHECKS</code> pattern.
            This cannot be undone.
          </Alert>
          <div className="flex gap-10" style={{ marginTop: 12 }}>
            <button className="btn btn-danger" onClick={() => remove(confirmDel)}>Delete Permanently</button>
            <button className="btn btn-ghost" onClick={() => setConfirmDel(null)}>Cancel</button>
          </div>
        </Modal>
      )}
    </div>
  );
}


// ── Registrar: Faculty Review (instructor questioning) ─────────────────────

export function RegistrarInstructorReviews() {
  const [data, setData] = useState([]);
  const [msg, setMsg] = useState(null);
  const [reasonMap, setReasonMap] = useState({});
  const load = useCallback(() => {
    api.get('/registrar/instructor-reviews').then(r => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (uid, action) => {
    setMsg(null);
    try {
      const r = await api.post('/registrar/instructor-action', { userId: uid, action, reason: reasonMap[uid] || '' });
      setMsg({ ok: r.data.ok, text: r.data.msg });
      load();
    } catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Faculty Review</h1>
        <p className="page-subtitle">Instructors flagged for review when class GPA exceeds 3.5 or falls below 2.5. Question them, accept their justification, or take action.</p>
      </div>
      {msg && <Alert variant={msg.ok ? 'success' : 'danger'}>{msg.text}</Alert>}
      {data.length === 0 ? (
        <div className="empty-state">No instructors currently flagged for review.</div>
      ) : (
        data.map(inst => (
          <div key={inst.userId} className="card" style={{ marginBottom: 16, borderLeft: '4px solid var(--danger)' }}>
            <div className="flex items-center gap-12" style={{ marginBottom: 10, flexWrap: 'wrap' }}>
              <strong style={{ color: 'var(--navy)', fontSize: 15 }}>{inst.name}</strong>
              <span style={{ fontSize: 12, color: 'var(--text3)' }}>{inst.userId}</span>
              <Badge variant="warning">{inst.warnings}/3 warnings</Badge>
              {inst.suspended && <Badge variant="danger">SUSPENDED</Badge>}
            </div>
            <Table
              headers={['Course', 'Course Name', 'Class GPA', 'Graded Students']}
              rows={inst.extremeClasses.map(c => [
                c.courseCode, c.courseName, c.classGpa, c.studentCount
              ])}
              colorFn={(val, ci) => ci === 2 ? (val > 3.5 ? 'var(--green)' : val < 2.5 ? 'var(--danger)' : null) : null}
            />
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Reason (used for warn/fire actions)</label>
              <input className="form-input"
                placeholder="e.g. 'Class GPA of 1.5 unjustified after meeting'"
                value={reasonMap[inst.userId] || ''}
                onChange={e => setReasonMap(m => ({ ...m, [inst.userId]: e.target.value }))} />
            </div>
            <div className="flex gap-10" style={{ flexWrap: 'wrap' }}>
              <button className="btn btn-green btn-sm" onClick={() => act(inst.userId, 'clear')}>✓ Clear (Justification Accepted)</button>
              <button className="btn btn-warning btn-sm" onClick={() => act(inst.userId, 'warn')}>⚠️ Warn</button>
              <button className="btn btn-danger btn-sm" onClick={() => act(inst.userId, 'fire')}>🚫 Fire</button>
            </div>
          </div>
        ))
      )}
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
  const [rejectJustification, setRejectJustification] = useState('');
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    api.get('/registrar/applications').then(r => setApps(r.data));
    api.get('/registrar/complaints').then(r => setComplaints(r.data));
    api.get('/registrar/reviews').then(r => setReviews(r.data));
    api.get('/registrar/taboo').then(r => setTabooWords(r.data));
  }, []);
  useEffect(() => { load(); }, [load]);

  const approveApp = async (appId) => {
    try { const r = await api.post('/registrar/approve-app', { appId, justification }); setMsg({ ok: r.data.ok, text: r.data.msg }); if (r.data.ok) setJustification(''); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Cannot approve.' }); }
  };
  const rejectApp = async (appId) => {
    try { const r = await api.post('/registrar/reject-app', { appId, justification: rejectJustification }); setMsg({ ok: r.data.ok, text: r.data.msg }); if (r.data.ok) setRejectJustification(''); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };
  const resolveComplaint = async (action) => {
    if (!cid) { setMsg({ ok: false, text: 'Enter complaint ID.' }); return; }
    try { const r = await api.post('/registrar/resolve-complaint', { complaintId: cid, action }); setMsg({ ok: r.data.ok, text: r.data.msg }); load(); }
    catch (e) { setMsg({ ok: false, text: e.response?.data?.error || 'Error' }); }
  };
  const addTaboo = async () => {
    if (!tabooInput.trim()) return;
    try { const r = await api.post('/registrar/taboo', { word: tabooInput.trim() }); setTabooWords(r.data.tabooWords); setTabooInput(''); load(); }
    catch { }
  };
  const removeTaboo = async (word) => {
    try { const r = await api.delete(`/registrar/taboo/${word}`); setTabooWords(r.data.tabooWords); load(); }
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
          <Alert variant="info">
            <strong>Auto-accept rule:</strong> Students with GPA &gt; 3.0 and program quota not reached are accepted without justification.
            Overriding the rule (approving below threshold/over quota, or rejecting a qualified applicant) requires a justification.
          </Alert>
          <div className="grid-2 gap-12" style={{ marginBottom: 16 }}>
            <div className="form-group">
              <label className="form-label">Approve Justification (if needed)</label>
              <input className="form-input" placeholder="e.g. 'Strong portfolio compensates for GPA'" value={justification} onChange={e => setJustification(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Reject Justification (if needed)</label>
              <input className="form-input" placeholder="e.g. 'References did not check out'" value={rejectJustification} onChange={e => setRejectJustification(e.target.value)} />
            </div>
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
          <div className="section-title" style={{ marginTop: 24 }}>Processed Applications</div>
          <Table
            headers={['ID', 'Name', 'Role', 'GPA', 'Status']}
            rows={apps.filter(a => a.status !== 'Pending').map(a => [
              a.appId, a.name, a.role, a.gpa.toFixed(2), a.status
            ])}
            colorFn={(val, ci) => ci === 4 ? (val === 'Approved' ? 'var(--green)' : 'var(--danger)') : null}
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
              if (ci === 3 && String(val).includes('Instructor')) return 'var(--warning)';
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
          <Alert variant="info">
            <strong>Reviews displayed are masked.</strong> The "Visible Text" column shows what public viewers see (taboo words replaced with asterisks). Hidden reviews (3+ taboo words) are not shown publicly at all. You can see the original text on hover.
          </Alert>
          <Table
            headers={['Course', 'Student', 'Rating', 'Visible Text', 'Taboo', 'Status']}
            rows={reviews.map(r => [
              r.courseCode, r.studentId, `${r.rating} ★`,
              <span key={r.reviewId} title={`Original: ${r.text}`}>
                {r.visibleText.length > 60 ? r.visibleText.slice(0,60)+'...' : r.visibleText}
              </span>,
              r.tabooCount,
              r.hidden ? 'Hidden' : r.flagged ? 'Masked' : 'Visible'
            ])}
            colorFn={(val, ci) => ci === 5 ? (val === 'Hidden' ? 'var(--danger)' : val === 'Masked' ? 'var(--warning)' : 'var(--green)') : null}
          />
          <div className="card" style={{ marginTop: 20 }}>
            <div className="section-title">Taboo Word List</div>
            <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 12 }}>
              Adding or removing a taboo word automatically re-scans all existing reviews.
            </p>
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
    catch { setResult({ answer: 'Error contacting AI.', source: 'none', local: false }); }
    setLoading(false);
  };

  // Role-scoped suggestions
  const generalSuggestions = [
    'What are the graduation requirements?',
    'How does the warning system work?',
    'What are the semester phases?',
    'How do course reviews work?',
    'What is the Study Buddy Matcher?',
  ];
  const studentSuggestions = [
    'What is my current GPA?',
    'What classes am I taking?',
    'How many warnings do I have?',
  ];
  const instructorSuggestions = [
    'Who are my students?',
    'What is my class average?',
  ];
  const suggestions = user?.role === 'Student'
    ? [...studentSuggestions, ...generalSuggestions]
    : user?.role === 'Instructor'
      ? [...instructorSuggestions, ...generalSuggestions]
      : generalSuggestions;

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="page-header">
        <h1 className="page-title">AI Assistant</h1>
        <p className="page-subtitle">Ask questions about College0 — answered from local knowledge, with LLM fallback for unknown questions.</p>
      </div>

      <div className="card">
        <form onSubmit={ask}>
          <div className="form-group">
            <label className="form-label">Your Question</label>
            <textarea className="form-input" rows={3} placeholder={
              user?.role === 'Student'
                ? "Try: 'What is my current GPA?' or 'How do course reviews work?'"
                : user?.role === 'Instructor'
                  ? "Try: 'Who are my students?' or 'What is my class average?'"
                  : "Try: 'What are the graduation requirements?'"
            } value={q} onChange={e => setQ(e.target.value)} />
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
            <div className="form-label" style={{ marginBottom: 8 }}>
              Answer
              {result.source === 'live' && <Badge variant="green">Personalized · Live Data</Badge>}
              {result.source === 'local' && <Badge variant="navy">Knowledge Base</Badge>}
              {result.source === 'llm' && <Badge variant="warning">LLM Fallback</Badge>}
              {result.source === 'none' && <Badge variant="danger">No Answer</Badge>}
            </div>
            <div className="card" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.6, margin: 0 }}>{result.answer}</pre>
            </div>
            {result.source === 'live' && (
              <div className="alert alert-success" style={{ marginTop: 12 }}>
                ✅ Answered from your live College0 record.
              </div>
            )}
            {result.source === 'local' && (
              <div className="alert alert-success" style={{ marginTop: 12 }}>
                ✅ Sourced from the College0 local knowledge base
                {result.score && ` (relevance: ${result.score})`}.
              </div>
            )}
            {result.source === 'llm' && (
              <div className="alert alert-warning" style={{ marginTop: 12 }}>
                {result.warning || '⚠️ This answer is from a general LLM and may include hallucinations.'}
              </div>
            )}
            {result.source === 'none' && (
              <div className="alert alert-info" style={{ marginTop: 12 }}>
                💡 No confident answer found. Try rephrasing your question.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
