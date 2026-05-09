import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

export default function MyCourses() {
  const { sem } = useAuth();
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const load = () => api.get('/my-courses').then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const act = async (action, section_id) => {
    setBusy(true); setMsg('');
    try {
      const r = await api.post('/my-courses', { action, section_id });
      setMsg(r.data.msg || '');
      load();
    } catch (err) {
      setMsg(err.response?.data?.msg || 'An error occurred.');
    } finally { setBusy(false); }
  };

  if (!data) return <div className="loading">Loading…</div>;

  const { current_enrollments, all_sections, enrolled_section_ids, waitlisted_ids, special_reg } = data;
  const canEnroll = sem?.phase === 'registration' || (sem?.phase === 'running' && special_reg);

  return (
    <>
      <div className="page-header">
        <h1>My Courses</h1>
        <p>Manage your course registrations for {sem?.term_name} {sem?.year}.</p>
      </div>

      {special_reg && sem?.phase === 'running' && (
        <div className="alert alert-warning" style={{ marginBottom: 16 }}>
          ⚡ <strong>Special Re-Registration:</strong> One or more of your courses were cancelled due to low enrollment.
          You have a one-time opportunity to enroll in another open section. Please choose a replacement course below.
        </div>
      )}

      {msg && <div className="alert alert-info">{msg}</div>}

      <div className="section-title">Enrolled This Semester</div>
      <div className="table-wrap" style={{ marginBottom: 20 }}>
        <table>
          <thead>
            <tr><th>Code</th><th>Course Title</th><th>Schedule</th><th>Room</th><th>Instructor</th><th>Credits</th><th></th></tr>
          </thead>
          <tbody>
            {current_enrollments.length === 0 && (
              <tr><td colSpan={7} style={{ color: 'var(--muted)', padding: 18 }}>Not enrolled in any sections this semester.</td></tr>
            )}
            {current_enrollments.map(e => (
              <tr key={e.enrollment_id}>
                <td><strong>{e.code}</strong></td>
                <td>{e.title}</td>
                <td>{e.schedule_slot}</td>
                <td>{e.room}</td>
                <td>{e.instructor_name}</td>
                <td>{e.credit_hours}</td>
                <td>
                  {sem?.phase === 'registration'
                    ? <button className="btn-secondary btn-sm" disabled={busy} onClick={() => act('drop', e.section_id)}>Drop</button>
                    : '—'
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {canEnroll && (
        <>
          <div className="section-title" style={{ marginTop: 24 }}>
            {special_reg && sem?.phase === 'running' ? '⚡ Special Re-Registration — Available Sections' : 'Available Sections'}
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Code</th><th>Course Title</th><th>Schedule</th><th>Room</th><th>Instructor</th><th>Seats</th><th>Core</th><th></th></tr>
              </thead>
              <tbody>
                {all_sections.filter(s => !enrolled_section_ids.includes(s.section_id)).map(s => (
                  <tr key={s.section_id}>
                    <td><strong>{s.code}</strong></td>
                    <td>{s.title}</td>
                    <td>{s.schedule_slot}</td>
                    <td>{s.room}</td>
                    <td>{s.instructor_name}</td>
                    <td>{s.enrolled_count}/{s.capacity}</td>
                    <td>{s.is_core ? <span className="badge-core">★ Core</span> : '—'}</td>
                    <td>
                      {waitlisted_ids.includes(s.section_id)
                        ? <span style={{ color: 'var(--orange)', fontSize: '0.78rem', fontWeight: 600 }}>On Waitlist</span>
                        : <button
                            className={s.status === 'full' ? 'btn-secondary btn-sm' : 'btn-primary btn-sm'}
                            disabled={busy}
                            onClick={() => act('enroll', s.section_id)}
                          >
                            {s.status === 'full' ? 'Join Waitlist' : 'Enroll'}
                          </button>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!canEnroll && (
        <div className="alert alert-info" style={{ marginTop: 16 }}>
          Enrollment is only available during the <strong>Registration</strong> phase. Current phase: <strong>{sem?.phase}</strong>.
        </div>
      )}
    </>
  );
}
