import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

export default function Instructor() {
  const { user, sem } = useAuth();
  const [data, setData] = useState(null);
  const [grades, setGrades] = useState({});
  const [msg, setMsg] = useState('');

  const load = () => api.get('/instructor').then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const saveGrade = async (enrollmentId) => {
    const grade = grades[enrollmentId];
    if (!grade) return;
    try {
      const r = await api.post('/instructor/grade', { enrollment_id: enrollmentId, grade });
      setMsg(r.data.msg);
      load();
    } catch (err) { setMsg(err.response?.data?.msg || 'Error saving grade.'); }
  };

  if (!data) return <div className="loading">Loading…</div>;

  return (
    <>
      <div className="page-header">
        <h1>My Classes</h1>
        <p>{user?.first_name} {user?.last_name} · Instructor · {sem?.term_name} {sem?.year}</p>
      </div>

      {msg && <div className="alert alert-success">{msg}</div>}

      {data.sections_data.length === 0 && (
        <div className="alert alert-info">You are not assigned to any sections this semester.</div>
      )}

      {data.sections_data.map(sd => (
        <div className="table-wrap" key={sd.section.section_id} style={{ marginBottom: 28 }}>
          <div className="table-title">
            {sd.section.code} — {sd.section.title}
            <span style={{ fontSize: '0.78rem', color: 'var(--muted)', fontWeight: 400, marginLeft: 12 }}>
              {sd.section.schedule_slot} · {sd.section.room} · {sd.section.enrolled_count}/{sd.section.capacity} enrolled
            </span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Student ID</th><th>Name</th><th>Status</th><th>Grade</th>
                {sem?.phase === 'grading' && <th>Assign Grade</th>}
              </tr>
            </thead>
            <tbody>
              {sd.students.length === 0 && (
                <tr><td colSpan={5} style={{ color: 'var(--muted)', padding: 16 }}>No students enrolled.</td></tr>
              )}
              {sd.students.map(s => (
                <tr key={s.student_id}>
                  <td>#{s.student_id}</td>
                  <td>{s.name}</td>
                  <td>{s.enrollment_status}</td>
                  <td>{s.letter_grade || '—'}</td>
                  {sem?.phase === 'grading' && (
                    <td>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                          className="grade-select"
                          value={grades[s.enrollment_id] ?? (s.letter_grade || '')}
                          onChange={e => setGrades(g => ({ ...g, [s.enrollment_id]: e.target.value }))}
                        >
                          <option value="">— Select —</option>
                          {['A+','A','A-','B+','B','B-','C+','C','C-','D+','D','F'].map(g => (
                            <option key={g} value={g}>{g}</option>
                          ))}
                        </select>
                        <button className="btn-primary btn-sm" onClick={() => saveGrade(s.enrollment_id)}>Save</button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}
