import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

function StudentRecordModal({ student, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Academic Record — {student.name}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="stats-row" style={{ marginBottom: 16 }}>
            <div className="stat-card" style={{ flex: 1 }}>
              <div className="stat-label">Cum. GPA</div>
              <div className="stat-value green">{Number(student.cumulative_gpa).toFixed(3)}</div>
            </div>
            <div className="stat-card" style={{ flex: 1 }}>
              <div className="stat-label">Sem. GPA</div>
              <div className="stat-value green">{Number(student.semester_gpa).toFixed(3)}</div>
            </div>
            <div className="stat-card" style={{ flex: 1 }}>
              <div className="stat-label">Warnings</div>
              <div className="stat-value" style={{ color: student.warning_count > 0 ? 'var(--orange)' : undefined }}>
                {student.warning_count}/3
              </div>
            </div>
            <div className="stat-card" style={{ flex: 1 }}>
              <div className="stat-label">Honors</div>
              <div className="stat-value" style={{ color: '#7c3aed' }}>{student.honor_count}</div>
            </div>
          </div>
          <div className="section-title">Grade History</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ borderBottom: '1.5px solid var(--border)' }}>
                <th style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}>Code</th>
                <th style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}>Title</th>
                <th style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}>Grade</th>
                <th style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}>Semester</th>
              </tr>
            </thead>
            <tbody>
              {student.grade_history.length === 0 && (
                <tr><td colSpan={4} style={{ padding: '14px 8px', color: 'var(--muted)' }}>No completed courses.</td></tr>
              )}
              {student.grade_history.map((h, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '7px 8px' }}><strong>{h.code}</strong></td>
                  <td style={{ padding: '7px 8px' }}>{h.title}</td>
                  <td style={{ padding: '7px 8px', fontWeight: 700 }}>{h.letter_grade}</td>
                  <td style={{ padding: '7px 8px', color: 'var(--muted)' }}>{h.term_name} {h.year}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ComplaintModal({ student, sectionId, onClose, onSubmit }) {
  const [action, setAction] = useState('warn');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const handleSubmit = async e => {
    e.preventDefault();
    if (!text.trim()) { setErr('Please describe the issue.'); return; }
    setBusy(true); setErr('');
    try {
      await api.post('/instructor/student-complaint', {
        student_id: student.student_id,
        section_id: sectionId,
        requested_action: action,
        complaint_text: text,
      });
      onSubmit('Complaint filed. The Registrar will review it and take action.');
      onClose();
    } catch (err) {
      setErr(err.response?.data?.msg || 'Error filing complaint.');
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" style={{ maxWidth: 480 }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>File Complaint Against {student.name}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {err && <div className="alert alert-error" style={{ marginBottom: 12 }}>{err}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Requested Action</label>
              <select value={action} onChange={e => setAction(e.target.value)}>
                <option value="warn">Warn the student</option>
                <option value="deregister">De-register the student from my class</option>
              </select>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea value={text} onChange={e => setText(e.target.value)} placeholder="Describe the issue in detail..." style={{ minHeight: 100 }} required />
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: 14 }}>
              The Registrar will review this and may either take action against the student or warn you if the complaint is unfounded.
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button type="submit" className="btn-primary" disabled={busy}>Submit Complaint</button>
              <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

const PHASE_COLORS = {
  grading:      { bg: '#f0fdf4', color: '#166534', border: '#bbf7d0' },
  running:      { bg: '#eff6ff', color: '#1e40af', border: '#bfdbfe' },
  registration: { bg: '#fef3c7', color: '#92400e', border: '#fde68a' },
  setup:        { bg: '#f3f4f6', color: '#374151', border: '#e5e7eb' },
  closed:       { bg: '#f3f4f6', color: '#9ca3af', border: '#e5e7eb' },
};

export default function Instructor() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [grades, setGrades] = useState({});
  const [msg, setMsg] = useState('');
  const [viewStudent, setViewStudent] = useState(null);
  const [complaintTarget, setComplaintTarget] = useState(null);

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

  const canGrade = (phase) => ['running', 'grading'].includes(phase);

  return (
    <>
      {viewStudent && <StudentRecordModal student={viewStudent} onClose={() => setViewStudent(null)} />}
      {complaintTarget && (
        <ComplaintModal
          student={complaintTarget.student}
          sectionId={complaintTarget.sectionId}
          onClose={() => setComplaintTarget(null)}
          onSubmit={m => setMsg(m)}
        />
      )}

      <div className="page-header">
        <h1>My Classes</h1>
        <p>{user?.first_name} {user?.last_name} · Instructor</p>
        {data.instructor?.suspension_next_semester === 1 && (
          <div className="alert alert-error" style={{ marginTop: 12 }}>
            ⚠ Your teaching privileges are suspended for the next semester due to all assigned courses being cancelled.
          </div>
        )}
      </div>

      {msg && <div className="alert alert-success" style={{ marginBottom: 16 }}>{msg}</div>}

      {data.semesters_data.length === 0 && (
        <div className="alert alert-info">You are not assigned to any active sections.</div>
      )}

      {data.semesters_data.map(({ sem, sections_data }) => {
        const phaseStyle = PHASE_COLORS[sem.phase] || PHASE_COLORS.closed;
        return (
          <div key={sem.semester_id} style={{ marginBottom: 36 }}>
            {/* Semester header */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
              paddingBottom: 10, borderBottom: '2px solid var(--border)'
            }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>
                {sem.term_name} {sem.year}
              </h2>
              <span style={{
                fontSize: '0.72rem', fontWeight: 700, padding: '3px 10px', borderRadius: 20,
                background: phaseStyle.bg, color: phaseStyle.color,
                border: `1px solid ${phaseStyle.border}`, textTransform: 'uppercase', letterSpacing: '0.5px'
              }}>
                {sem.phase}
              </span>
              {canGrade(sem.phase) && (
                <span style={{ fontSize: '0.75rem', color: 'var(--green)', fontWeight: 600 }}>
                  ✓ Grade entry available
                </span>
              )}
            </div>

            {sections_data.length === 0 && (
              <div className="alert alert-info">No sections this semester.</div>
            )}

            {sections_data.map(sd => (
              <div className="table-wrap" key={sd.section.section_id} style={{ marginBottom: 22 }}>
                <div className="table-title">
                  {sd.section.code} — {sd.section.title}
                  {sd.section.status === 'cancelled' && (
                    <span style={{ marginLeft: 10, fontSize: '0.72rem', background: 'var(--red)', color: '#fff', padding: '2px 8px', borderRadius: 4 }}>CANCELLED</span>
                  )}
                  <span style={{ fontSize: '0.78rem', color: 'var(--muted)', fontWeight: 400, marginLeft: 12 }}>
                    {sd.section.schedule_slot} · {sd.section.room} · {sd.section.enrolled_count}/{sd.section.capacity} enrolled
                  </span>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Cum. GPA</th>
                      <th>Warnings</th>
                      <th>Status</th>
                      <th>Current Grade</th>
                      {canGrade(sem.phase) && <th>Assign Grade</th>}
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sd.students.length === 0 && (
                      <tr><td colSpan={canGrade(sem.phase) ? 7 : 6} style={{ color: 'var(--muted)', padding: 16 }}>No students enrolled.</td></tr>
                    )}
                    {sd.students.map(s => (
                      <tr key={s.student_id}>
                        <td><strong>{s.name}</strong></td>
                        <td style={{ color: 'var(--green)', fontWeight: 600 }}>{Number(s.cumulative_gpa || 0).toFixed(3)}</td>
                        <td style={{ color: s.warning_count > 0 ? 'var(--orange)' : undefined, fontWeight: s.warning_count > 0 ? 600 : undefined }}>
                          {s.warning_count}/3
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{s.enrollment_status}</td>
                        <td style={{ fontWeight: 700, color: s.letter_grade ? 'var(--blue)' : 'var(--muted)' }}>
                          {s.letter_grade || '—'}
                        </td>
                        {canGrade(sem.phase) && (
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
                              <button
                                className="btn-primary btn-sm"
                                disabled={!grades[s.enrollment_id]}
                                onClick={() => saveGrade(s.enrollment_id)}
                              >
                                Save
                              </button>
                            </div>
                          </td>
                        )}
                        <td>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button className="btn-secondary btn-sm" onClick={() => setViewStudent(s)}>Records</button>
                            <button
                              className="btn-sm"
                              style={{ background: '#fee2e2', color: 'var(--red)', border: '1px solid #fca5a5', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                              onClick={() => setComplaintTarget({ student: s, sectionId: sd.section.section_id })}
                            >
                              Complain
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        );
      })}
    </>
  );
}
