import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

export default function Home() {
  const { setLoginOpen } = useAuth();
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
              <th>Schedule</th><th>Room</th><th>Enrolled</th><th>Core</th><th>Status</th>
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
                  {s.status === 'open' && <span className="badge-status-avail">Open</span>}
                  {s.status === 'full' && <span style={{ color: 'var(--orange)', fontWeight: 600 }}>Full</span>}
                  {s.status === 'completed' && <span style={{ color: 'var(--muted)', fontWeight: 600 }}>Completed</span>}
                  {!['open','full','completed'].includes(s.status) && s.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <button className="btn-primary" onClick={() => setLoginOpen(true)}>
          Sign In to Access Your Portal →
        </button>
      </div>
    </>
  );
}
