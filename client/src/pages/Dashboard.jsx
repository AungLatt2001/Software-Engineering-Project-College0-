import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../App';
import api from '../api';

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => { api.get('/dashboard').then(r => setData(r.data)).catch(() => {}); }, []);

  if (!data) return <div className="loading">Loading…</div>;
  const { st } = data;

  return (
    <>
      <div className="banner">
        <h1>Welcome back, {user?.first_name} {user?.last_name}</h1>
        <p>
          #{user?.user_id} · Student Portal ·{' '}
          {user?.status === 'suspended'
            ? <span style={{ color: '#fca5a5' }}>⚠ Account Suspended</span>
            : user?.status === 'graduated' ? '🎓 Graduated' : 'Active'}
        </p>
      </div>

      {st?.fine_due > 0 && (
        <div className="alert alert-error" style={{ marginBottom: 20 }}>
          ⚠ Outstanding fine: <strong>${Number(st.fine_due).toFixed(2)}</strong> — Contact the Registrar's office.
        </div>
      )}

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Cumulative GPA</div>
          <div className="stat-value green">{Number(st?.cumulative_gpa).toFixed(3)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Semester GPA</div>
          <div className="stat-value green">{Number(st?.semester_gpa).toFixed(3)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Warnings</div>
          <div className="stat-value" style={{ color: user?.warning_count > 0 ? 'var(--orange)' : undefined }}>
            {user?.warning_count}/3
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Honors</div>
          <div className="stat-value" style={{ color: '#7c3aed' }}>{st?.honor_count}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Enrolled</div>
          <div className="stat-value">{data.enrolled}</div>
          <div className="stat-sub">This semester</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Completed</div>
          <div className="stat-value">{data.completed}</div>
          <div className="stat-sub">Courses</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, maxWidth: 680 }}>
        {[
          ['/my-courses', '📚', 'My Courses', 'View and manage your enrolled sections for this semester.'],
          ['/transcript', '📋', 'Transcript', 'View your full grade history and academic standing.'],
          ['/reviews', '⭐', 'Reviews & More', 'Submit course reviews, graduation request, or complaints.'],
          ['/ai-assistant', '🤖', 'AI Assistant', 'Ask questions about your academic portal and requirements.'],
        ].map(([to, icon, title, desc]) => (
          <Link to={to} key={to} style={{ textDecoration: 'none' }}>
            <div className="col-card" style={{ cursor: 'pointer', height: '100%' }}>
              <div className="col-card-title"><span className="icon">{icon}</span> {title}</div>
              <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>{desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
