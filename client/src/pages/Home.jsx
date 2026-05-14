import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../App';
import api from '../api';

const VISITOR_STEPS = [
  {
    num: '1',
    icon: '👀',
    title: 'Browse the Course Catalogue',
    desc: 'Scroll down to see all available course sections, schedules, instructors, and enrollment numbers — no login required.',
    action: null,
  },
  {
    num: '2',
    icon: '📝',
    title: 'Submit an Application',
    desc: 'Click "Apply Now" to submit a visitor application as a prospective student or instructor. Students need a prior GPA above 3.0.',
    action: { label: 'Apply Now →', to: '/apply' },
  },
  {
    num: '3',
    icon: '⏳',
    title: 'Wait for Registrar Approval',
    desc: 'A Registrar will review your application and approve or reject it. You\'ll receive your login credentials once approved.',
    action: null,
  },
  {
    num: '4',
    icon: '🔑',
    title: 'Sign In & Get Started',
    desc: 'Once approved, sign in with your college email. Students get a step-by-step tutorial on their first login to guide them through everything.',
    action: { label: 'Sign In →', login: true },
  },
];

const ROLE_CARDS = [
  {
    icon: '🎓',
    role: 'Students',
    color: '#1e3a5f',
    features: [
      'Enroll in and drop courses during Registration',
      'Track GPA, warnings, and honor count on Dashboard',
      'View full transcript and grade history',
      'Submit anonymous course reviews',
      'Apply for graduation',
      'File complaints or ask the AI Assistant',
    ],
  },
  {
    icon: '📚',
    role: 'Instructors',
    color: '#166534',
    features: [
      'View enrolled students across all active semesters',
      'Post and update student grades during Grading phase',
      'Access student academic records and GPA history',
      'File complaints against students in your class',
      'Receive notifications on section cancellations',
    ],
  },
  {
    icon: '🏛️',
    role: 'Registrars',
    color: '#92400e',
    features: [
      'Control semester phases (Setup → Registration → Running → Grading → Closed)',
      'Approve or reject visitor applications',
      'Issue manual warnings and manage suspensions',
      'Resolve student and instructor complaints',
      'Approve graduation applications',
    ],
  },
];

export default function Home() {
  const { user, setLoginOpen } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => { api.get('/home').then(r => setData(r.data)).catch(() => {}); }, []);

  if (!data) return <div className="loading">Loading…</div>;

  const sem = data.sem;
  const stars = n => '★'.repeat(Math.round(n || 0));

  return (
    <>
      <div className="banner">
        <h1>Welcome to College0</h1>
        <p>An AI-enabled academic management portal for students, instructors, and administrators.</p>
      </div>

      {/* ── VISITOR TUTORIAL — only shown when not logged in ── */}
      {!user && (
        <div className="visitor-guide">
          <div className="visitor-guide-header">
            <div className="visitor-guide-badge">New to College0?</div>
            <h2 className="visitor-guide-title">Here's how to get started</h2>
            <p className="visitor-guide-sub">
              College0 is an academic portal where students, instructors, and registrars manage courses, grades, and academic records.
              As a visitor, follow these steps to join.
            </p>
          </div>

          <div className="visitor-steps">
            {VISITOR_STEPS.map(step => (
              <div className="visitor-step" key={step.num}>
                <div className="visitor-step-num">{step.num}</div>
                <div className="visitor-step-icon">{step.icon}</div>
                <div className="visitor-step-body">
                  <div className="visitor-step-title">{step.title}</div>
                  <div className="visitor-step-desc">{step.desc}</div>
                  {step.action && (
                    step.action.login
                      ? <button className="visitor-step-btn" onClick={() => setLoginOpen(true)}>{step.action.label}</button>
                      : <Link to={step.action.to} className="visitor-step-btn">{step.action.label}</Link>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Role overview */}
          <div className="visitor-roles">
            {ROLE_CARDS.map(card => (
              <div className="visitor-role-card" key={card.role}>
                <div className="visitor-role-icon" style={{ background: card.color }}>{card.icon}</div>
                <div className="visitor-role-title">{card.role}</div>
                <ul className="visitor-role-list">
                  {card.features.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              </div>
            ))}
          </div>

          {/* Phase explanation */}
          <div className="visitor-phases">
            <div className="visitor-phases-title">📅 Understanding Semester Phases</div>
            <div className="visitor-phase-row">
              {[
                { phase: 'Setup', desc: 'Admin configures sections and assigns instructors.', color: '#6b7280' },
                { phase: 'Registration', desc: 'Students enroll in or drop courses.', color: '#2563eb' },
                { phase: 'Running', desc: 'Classes are in session. Low-enrollment courses may be cancelled.', color: '#7c3aed' },
                { phase: 'Grading', desc: 'Instructors post grades; students submit reviews.', color: '#d97706' },
                { phase: 'Closed', desc: 'Semester is archived and finalized.', color: '#6b7280' },
              ].map((p, i, arr) => (
                <React.Fragment key={p.phase}>
                  <div className="visitor-phase-item">
                    <div className="visitor-phase-dot" style={{ background: p.color }} />
                    <div className="visitor-phase-name" style={{ color: p.color }}>{p.phase}</div>
                    <div className="visitor-phase-desc">{p.desc}</div>
                  </div>
                  {i < arr.length - 1 && <div className="visitor-phase-arrow">→</div>}
                </React.Fragment>
              ))}
            </div>
          </div>

          <div className="visitor-cta">
            <Link to="/apply" className="btn-primary" style={{ textDecoration: 'none', padding: '11px 28px', fontSize: '0.92rem' }}>
              Apply to Join College0
            </Link>
            <button className="btn-secondary" style={{ padding: '11px 24px', fontSize: '0.92rem' }} onClick={() => setLoginOpen(true)}>
              Sign In
            </button>
            <Link to="/ai-assistant" className="btn-secondary" style={{ textDecoration: 'none', padding: '11px 24px', fontSize: '0.92rem' }}>
              Ask the AI Assistant
            </Link>
          </div>
        </div>
      )}

      {/* ── STATS ── */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Current Phase</div>
          <div className="stat-value" style={{ fontSize: '1.05rem', textTransform: 'capitalize' }}>{sem?.phase}</div>
          <div className="stat-sub">{sem?.term_name} {sem?.year}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Students</div>
          <div className="stat-value">{data.total_students}</div>
          <div className="stat-sub">Enrolled</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Sections</div>
          <div className="stat-value">{data.total_sections}</div>
          <div className="stat-sub">This semester</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Campus Avg GPA</div>
          <div className="stat-value green">{data.campus_gpa}</div>
          <div className="stat-sub">All students</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Faculty</div>
          <div className="stat-value">{data.total_faculty}</div>
          <div className="stat-sub">Instructors</div>
        </div>
      </div>

      <div className="three-col">
        <div className="col-card">
          <div className="col-card-title">🏆 Top Rated Courses</div>
          {data.top_rated.map((c, i) => (
            <div className="col-list-item" key={i}>
              <span className="item-name">{c.code} — {c.title}</span>
              <span className="stars">{stars(c.avg)}</span>
            </div>
          ))}
          {!data.top_rated.length && <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>No reviews yet.</div>}
        </div>
        <div className="col-card">
          <div className="col-card-title">⚠️ Needs Improvement</div>
          {data.needs_imp.map((c, i) => (
            <div className="col-list-item" key={i}>
              <span className="item-name">{c.code} — {c.title}</span>
              <span className="stars">{stars(c.avg)}</span>
            </div>
          ))}
          {!data.needs_imp.length && <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>No reviews yet.</div>}
        </div>
        <div className="col-card">
          <div className="col-card-title">🎓 Top GPA Students</div>
          {data.top_gpa.map((s, i) => (
            <div className="col-list-item" key={i}>
              <span className="item-name">{s.name}</span>
              <span className="item-meta">{Number(s.cumulative_gpa).toFixed(3)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="table-wrap">
        <div className="table-title">Course Sections — {sem?.term_name} {sem?.year}</div>
        <table>
          <thead>
            <tr>
              <th>Code</th><th>Course Title</th><th>Instructor</th>
              <th>Schedule</th><th>Room</th><th>Enrolled</th><th>Core</th>
              <th>Offered In</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.sections.map(s => (
              <tr key={s.section_id}>
                <td><strong>{s.code}</strong></td>
                <td>{s.title}</td>
                <td>{s.instructor_name}</td>
                <td>{s.schedule_slot}</td>
                <td>{s.room}</td>
                <td>{s.enrolled_count}/{s.capacity}</td>
                <td>{s.is_core ? <span className="badge-core">★ Core</span> : '—'}</td>
                <td>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {(s.offered_terms || '').split(',').map(t => (
                      <span key={t} style={{
                        fontSize: '0.65rem', fontWeight: 700, padding: '2px 7px', borderRadius: 10,
                        background: t.trim() === sem?.term_name ? '#dbeafe' : '#f3f4f6',
                        color: t.trim() === sem?.term_name ? '#1e40af' : '#6b7280',
                        border: t.trim() === sem?.term_name ? '1px solid #93c5fd' : '1px solid #e5e7eb',
                      }}>{t.trim()}</span>
                    ))}
                  </div>
                </td>
                <td>
                  {s.status === 'open' && <span className="badge-status-avail">Open</span>}
                  {s.status === 'full' && <span style={{ color: 'var(--orange)', fontWeight: 600 }}>Full</span>}
                  {s.status === 'cancelled' && <span style={{ color: 'var(--red)', fontWeight: 600 }}>Cancelled</span>}
                  {s.status === 'completed' && <span style={{ color: 'var(--muted)', fontWeight: 600 }}>Completed</span>}
                  {!['open','full','completed','cancelled'].includes(s.status) && s.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!user && (
        <div style={{ textAlign: 'center', padding: '24px 0 8px' }}>
          <Link to="/apply" className="btn-primary" style={{ textDecoration: 'none', padding: '11px 28px', marginRight: 12 }}>
            Apply to Join →
          </Link>
          <button className="btn-secondary" style={{ padding: '10px 24px' }} onClick={() => setLoginOpen(true)}>
            Sign In
          </button>
        </div>
      )}
    </>
  );
}
