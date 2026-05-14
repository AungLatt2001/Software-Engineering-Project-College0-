import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

const ALL_TERMS = ['Fall', 'Spring', 'Summer'];

const TERM_COLOR = {
  Fall:   { bg: '#fef3c7', color: '#92400e', border: '#fde68a' },
  Spring: { bg: '#d1fae5', color: '#065f46', border: '#6ee7b7' },
  Summer: { bg: '#fee2e2', color: '#991b1b', border: '#fca5a5' },
};

function TermBadge({ term }) {
  const c = TERM_COLOR[term] || { bg: '#f3f4f6', color: '#374151', border: '#e5e7eb' };
  return (
    <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 10, marginRight: 4,
      background: c.bg, color: c.color, border: `1px solid ${c.border}` }}>
      {term}
    </span>
  );
}

function CourseTermEditor({ course, onSave }) {
  const [selected, setSelected] = useState(
    (course.offered_terms || '').split(',').map(t => t.trim()).filter(Boolean)
  );
  const [busy, setBusy] = useState(false);
  const toggle = t => setSelected(s => s.includes(t) ? s.filter(x => x !== t) : [...s, t]);
  const save = async () => {
    if (!selected.length) return;
    setBusy(true);
    try {
      await api.post('/registrar/course-terms', { course_id: course.course_id, offered_terms: selected.join(',') });
      onSave(course.course_id, selected.join(','));
    } finally { setBusy(false); }
  };
  const changed = selected.sort().join() !== (course.offered_terms || '').split(',').map(t => t.trim()).sort().join();
  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
      {ALL_TERMS.map(t => (
        <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer',
          fontSize: '0.75rem', fontWeight: 600,
          color: selected.includes(t) ? TERM_COLOR[t].color : 'var(--muted)' }}>
          <input type="checkbox" checked={selected.includes(t)} onChange={() => toggle(t)} style={{ width: 13, height: 13 }} />
          {t}
        </label>
      ))}
      {changed && (
        <button className="btn-primary btn-sm" disabled={busy || !selected.length} onClick={save} style={{ padding: '3px 10px', fontSize: '0.72rem' }}>
          {busy ? '…' : 'Save'}
        </button>
      )}
    </div>
  );
}

export default function Registrar() {
  const { sem, setSem } = useAuth();
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState('');
  const [warningUser, setWarningUser] = useState('');
  const [warningReason, setWarningReason] = useState('');
  const [triggerResult, setTriggerResult] = useState(null);
  const [complaintNotes, setComplaintNotes] = useState({});

  // Section creation form state
  const [newSec, setNewSec] = useState({ semester_id: '', course_id: '', instructor_id: '', room: '', schedule_slot: '', capacity: 30 });
  const [secErr, setSecErr] = useState('');
  const [secBusy, setSecBusy] = useState(false);

  const load = () => api.get('/registrar').then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const updateCourseTerms = (courseId, terms) => {
    setData(d => ({ ...d, courses: d.courses.map(c => c.course_id === courseId ? { ...c, offered_terms: terms } : c) }));
    setMsg(`Course terms updated.`);
  };

  const createSection = async e => {
    e.preventDefault();
    setSecErr(''); setSecBusy(true);
    try {
      const r = await api.post('/registrar/section', { ...newSec, semester_id: parseInt(newSec.semester_id), course_id: parseInt(newSec.course_id), instructor_id: parseInt(newSec.instructor_id), capacity: parseInt(newSec.capacity) });
      setMsg(r.data.msg);
      setNewSec({ semester_id: '', course_id: '', instructor_id: '', room: '', schedule_slot: '', capacity: 30 });
      load();
    } catch (err) { setSecErr(err.response?.data?.msg || 'Error creating section.'); }
    finally { setSecBusy(false); }
  };

  // Figure out which terms a course is allowed in for the selected semester
  const selectedSemTerm = data?.all_semesters?.find(s => s.semester_id === parseInt(newSec.semester_id))?.term_name;
  const eligibleCourses = selectedSemTerm && data?.courses
    ? data.courses.filter(c => c.offered_terms.split(',').map(t => t.trim()).includes(selectedSemTerm))
    : data?.courses || [];

  const act = async (url, body) => {
    try {
      const r = await api.post(url, body);
      setMsg(r.data.msg || 'Done.');
      load();
      if (r.data.sem) setSem(r.data.sem);
      if (r.data.trigger_result) setTriggerResult(r.data.trigger_result);
    } catch (err) { setMsg(err.response?.data?.msg || 'Error.'); }
  };

  const resolveComplaint = async (cid, action) => {
    const note = complaintNotes[cid] || '';
    await act(`/registrar/complaint/${cid}`, { action, resolution_note: note });
  };

  if (!data) return <div className="loading">Loading…</div>;

  const PHASES = ['setup','registration','running','grading','closed'];
  const instructorComplaints = data.complaints.filter(c => c.complaint_type === 'instructor_vs_student');
  const generalComplaints = data.complaints.filter(c => c.complaint_type !== 'instructor_vs_student');

  return (
    <>
      <div className="page-header">
        <h1>Registrar Dashboard</h1>
        <p>Manage semesters, students, applications, complaints and graduation requests.</p>
      </div>

      {msg && <div className="alert alert-success">{msg}</div>}

      {triggerResult && (
        <div className="panel" style={{ borderLeft: '4px solid var(--orange)' }}>
          <div className="panel-title">⚡ Phase Trigger Report</div>
          <div style={{ fontSize: '0.82rem', lineHeight: 1.8 }}>
            <div>✅ Students warned for &lt;2 courses: <strong>{triggerResult.students_warned}</strong></div>
            <div>❌ Sections cancelled (fewer than 3 students): <strong>{triggerResult.sections_cancelled}</strong></div>
            <div>⚠️ Instructors warned: <strong>{triggerResult.instructors_warned}</strong></div>
            <div>🚫 Instructors suspended next semester: <strong>{triggerResult.instructors_suspended}</strong></div>
            <div>⚡ Students given special re-registration: <strong>{triggerResult.special_reg_granted}</strong></div>
            {triggerResult.details && triggerResult.details.length > 0 && (
              <ul style={{ marginTop: 8, paddingLeft: 18, color: 'var(--muted)' }}>
                {triggerResult.details.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            )}
          </div>
          <button className="btn-secondary btn-sm" style={{ marginTop: 10 }} onClick={() => setTriggerResult(null)}>Dismiss</button>
        </div>
      )}

      {/* SEMESTER CONTROL */}
      <div className="panel">
        <div className="panel-title">Semester Control</div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          {data.all_semesters.map(s => (
            <div key={s.semester_id} style={{ background: s.semester_id === sem?.semester_id ? 'var(--blue-soft)' : '#f8f9fb', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 18px', minWidth: 210 }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--muted)', marginBottom: 4 }}>{s.term_name} {s.year}</div>
              <span style={{ fontSize: '0.75rem', padding: '3px 10px', marginBottom: 10, display: 'inline-block', background: 'var(--blue)', color: '#fff', borderRadius: 20, fontWeight: 700, textTransform: 'uppercase' }}>{s.phase}</span>
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <select className="select-sm" defaultValue={s.phase} id={`phase-${s.semester_id}`}>
                  {PHASES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <button className="btn-primary btn-sm" onClick={() => {
                  const el = document.getElementById(`phase-${s.semester_id}`);
                  act('/registrar/phase', { semester_id: s.semester_id, phase: el.value });
                }}>Set</button>
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: '0.75rem', color: 'var(--muted)' }}>
          ⚡ Setting phase to <strong>running</strong> will automatically trigger: student warnings (&lt;2 courses), section cancellations (&lt;3 students), instructor warnings/suspensions, and special re-registration grants.
        </div>
      </div>

      {/* COURSE TERM AVAILABILITY */}
      <div className="panel">
        <div className="panel-title">📅 Course Term Availability</div>
        <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: 14 }}>
          Courses are only offered in specific semesters. Tick the checkboxes to update when a course can be scheduled.
          The system will block section creation if the course is not offered in that semester's term.
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
          <thead>
            <tr style={{ borderBottom: '1.5px solid var(--border)' }}>
              <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600, width: 90 }}>Code</th>
              <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}>Title</th>
              <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600, width: 50 }}>Credits</th>
              <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600, width: 50 }}>Core</th>
              <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}>Offered In (editable)</th>
            </tr>
          </thead>
          <tbody>
            {(data.courses || []).map(c => (
              <tr key={c.course_id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '8px 10px', fontWeight: 700 }}>{c.code}</td>
                <td style={{ padding: '8px 10px' }}>{c.title}</td>
                <td style={{ padding: '8px 10px', color: 'var(--muted)' }}>{c.credit_hours}</td>
                <td style={{ padding: '8px 10px' }}>{c.is_core ? <span style={{ color: 'var(--blue-mid)', fontWeight: 700 }}>★</span> : '—'}</td>
                <td style={{ padding: '8px 10px' }}>
                  <CourseTermEditor course={c} onSave={updateCourseTerms} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* CREATE NEW SECTION */}
      <div className="panel">
        <div className="panel-title">➕ Create New Section</div>
        <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: 14 }}>
          The course list below is automatically filtered to only show courses offered in the selected semester's term.
        </div>
        {secErr && <div className="alert alert-error" style={{ marginBottom: 12 }}>{secErr}</div>}
        <form onSubmit={createSection}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Semester</label>
              <select className="select-sm" value={newSec.semester_id} onChange={e => setNewSec(s => ({ ...s, semester_id: e.target.value, course_id: '' }))} required>
                <option value="">Select semester…</option>
                {data.all_semesters.filter(s => s.phase !== 'closed').map(s => (
                  <option key={s.semester_id} value={s.semester_id}>{s.term_name} {s.year}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>
                Course
                {selectedSemTerm && <span style={{ color: 'var(--muted)', fontWeight: 400, marginLeft: 6 }}>
                  ({eligibleCourses.length} available in {selectedSemTerm})
                </span>}
              </label>
              <select className="select-sm" value={newSec.course_id} onChange={e => setNewSec(s => ({ ...s, course_id: e.target.value }))} required disabled={!newSec.semester_id}>
                <option value="">Select course…</option>
                {eligibleCourses.map(c => (
                  <option key={c.course_id} value={c.course_id}>{c.code} — {c.title}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Instructor</label>
              <select className="select-sm" value={newSec.instructor_id} onChange={e => setNewSec(s => ({ ...s, instructor_id: e.target.value }))} required>
                <option value="">Select instructor…</option>
                {data.instructors.map(i => (
                  <option key={i.user_id} value={i.user_id}>{i.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Room</label>
              <input className="select-sm" value={newSec.room} onChange={e => setNewSec(s => ({ ...s, room: e.target.value }))} placeholder="e.g. Room 201" required />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Schedule</label>
              <input className="select-sm" value={newSec.schedule_slot} onChange={e => setNewSec(s => ({ ...s, schedule_slot: e.target.value }))} placeholder="e.g. MWF 10:00-11:00" required />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Capacity</label>
              <input type="number" className="select-sm" value={newSec.capacity} onChange={e => setNewSec(s => ({ ...s, capacity: e.target.value }))} min="1" max="200" required />
            </div>
          </div>
          {selectedSemTerm && !newSec.course_id && eligibleCourses.length === 0 && (
            <div className="alert alert-error" style={{ marginBottom: 10 }}>
              No courses are configured to be offered in {selectedSemTerm}. Update course term availability above first.
            </div>
          )}
          {selectedSemTerm && newSec.course_id && (
            <div style={{ fontSize: '0.74rem', color: 'var(--green)', fontWeight: 600, marginBottom: 10 }}>
              ✓ {data.courses.find(c => c.course_id === parseInt(newSec.course_id))?.code} is offered in {selectedSemTerm}
            </div>
          )}
          <button type="submit" className="btn-primary btn-sm" disabled={secBusy}>
            {secBusy ? 'Creating…' : 'Create Section'}
          </button>
        </form>
      </div>

      {/* SPECIAL REG STUDENTS */}
      {data.special_reg_students && data.special_reg_students.length > 0 && (
        <div className="panel" style={{ borderLeft: '4px solid var(--orange)' }}>
          <div className="panel-title">⚡ Special Re-Registration Students ({data.special_reg_students.length})</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: 10 }}>
            These students had courses cancelled and are eligible for special re-registration during the running phase.
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {data.special_reg_students.map(s => (
              <div key={s.user_id} style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '8px 14px', fontSize: '0.82rem' }}>
                <strong>{s.name}</strong>
                <span style={{ color: 'var(--muted)', marginLeft: 8 }}>#{s.user_id}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* INSTRUCTOR COMPLAINTS (must act) */}
      {instructorComplaints.length > 0 && (
        <div className="panel" style={{ borderLeft: '4px solid var(--red)' }}>
          <div className="panel-title">🚨 Instructor Complaints — Action Required ({instructorComplaints.length})</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: 12 }}>
            These were filed by instructors against students. You must take action: punish the student or warn the instructor if the complaint is unfounded.
          </div>
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead>
                <tr><th>Instructor</th><th>Student</th><th>Requested</th><th>Description</th><th>Status</th><th>Resolution Note</th><th>Action</th></tr>
              </thead>
              <tbody>
                {instructorComplaints.map(c => (
                  <tr key={c.complaint_id}>
                    <td>{c.filer_name}</td>
                    <td><strong>{c.target_name}</strong></td>
                    <td>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '2px 8px', borderRadius: 4, background: c.requested_action === 'deregister' ? '#fee2e2' : '#fef3c7', color: c.requested_action === 'deregister' ? 'var(--red)' : '#92400e' }}>
                        {c.requested_action === 'deregister' ? 'De-register' : 'Warn'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.78rem', maxWidth: 200 }}>{c.complaint_text}</td>
                    <td>
                      <span style={{ fontWeight: 600, color: c.status === 'resolved' ? 'var(--green)' : c.status === 'dismissed' ? 'var(--muted)' : 'var(--orange)' }}>
                        {c.status}
                      </span>
                    </td>
                    <td>
                      {['open','under_review'].includes(c.status) ? (
                        <input
                          placeholder="Resolution note..."
                          value={complaintNotes[c.complaint_id] || ''}
                          onChange={e => setComplaintNotes(n => ({ ...n, [c.complaint_id]: e.target.value }))}
                          style={{ padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, fontSize: '0.75rem', width: 160, fontFamily: 'inherit' }}
                        />
                      ) : <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{c.resolution_note || '—'}</span>}
                    </td>
                    <td>
                      {['open','under_review'].includes(c.status) ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <button className="btn-sm" style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 700 }}
                            onClick={() => resolveComplaint(c.complaint_id, 'warn_student')}>
                            ⚠ Warn Student
                          </button>
                          <button className="btn-sm" style={{ background: '#fee2e2', color: 'var(--red)', border: '1px solid #fca5a5', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 700 }}
                            onClick={() => resolveComplaint(c.complaint_id, 'deregister_student')}>
                            🚫 De-register Student
                          </button>
                          <button className="btn-sm" style={{ background: '#f3f4f6', color: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 700 }}
                            onClick={() => resolveComplaint(c.complaint_id, 'warn_instructor')}>
                            🔄 Warn Instructor
                          </button>
                        </div>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* WARNINGS */}
      {data.warnings.length > 0 && (
        <div className="panel">
          <div className="panel-title">Active Warnings ({data.warnings.length})</div>
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>User</th><th>Role</th><th>Reason</th><th>Source</th><th>Issued</th></tr></thead>
              <tbody>{data.warnings.map(w => (
                <tr key={w.warning_id}>
                  <td>{w.user_name}</td>
                  <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{w.user_role}</td>
                  <td>{w.reason}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{w.source_module.replace(/_/g,' ')}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{w.issued_at?.slice(0,10)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}

      {/* STUDENTS */}
      <div className="panel">
        <div className="panel-title">Students ({data.students.length})</div>
        <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Status</th><th>Cum GPA</th><th>Warnings</th><th>Honors</th><th>Fine</th></tr></thead>
            <tbody>{data.students.map(s => (
              <tr key={s.user_id}>
                <td>#{s.user_id}</td>
                <td>{s.name}</td>
                <td style={{ fontSize: '0.75rem' }}>{s.email}</td>
                <td><span style={{ color: s.status==='active' ? 'var(--green)' : s.status==='suspended' ? 'var(--red)' : 'var(--muted)', fontWeight: 600 }}>{s.status}</span></td>
                <td style={{ color: 'var(--green)', fontWeight: 600 }}>{Number(s.cumulative_gpa).toFixed(3)}</td>
                <td style={{ color: s.warning_count > 0 ? 'var(--orange)' : undefined, fontWeight: s.warning_count > 0 ? 600 : undefined }}>{s.warning_count}/3</td>
                <td>{s.honor_count}</td>
                <td>{s.fine_due > 0 ? <span style={{ color: 'var(--red)', fontWeight: 600 }}>${Number(s.fine_due).toFixed(2)}</span> : '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 8 }}>Issue Manual Warning</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="select-sm" style={{ minWidth: 180 }} value={warningUser} onChange={e => setWarningUser(e.target.value)}>
              <option value="">Select user...</option>
              {data.students.map(s => <option key={s.user_id} value={s.user_id}>{s.name}</option>)}
            </select>
            <input value={warningReason} onChange={e => setWarningReason(e.target.value)} placeholder="Reason for warning" style={{ flex: 1, minWidth: 200, padding: '6px 10px', border: '1.5px solid var(--border)', borderRadius: 6, fontSize: '0.82rem', fontFamily: 'inherit' }} />
            <button className="btn-secondary btn-sm" onClick={() => { act('/registrar/warning', { user_id: parseInt(warningUser), reason: warningReason }); setWarningUser(''); setWarningReason(''); }}>Issue Warning</button>
          </div>
        </div>
      </div>

      {/* INSTRUCTORS */}
      <div className="panel">
        <div className="panel-title">Instructors ({data.instructors.length})</div>
        <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Specialization</th><th>Status</th><th>Warnings</th><th>Suspended Next Sem.</th><th>Avg Rating</th></tr></thead>
            <tbody>{data.instructors.map(i => (
              <tr key={i.user_id}>
                <td>#{i.user_id}</td>
                <td>{i.name}</td>
                <td>{i.specialization || '—'}</td>
                <td><span style={{ color: i.status==='active' ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>{i.status}</span></td>
                <td style={{ color: i.warning_count > 0 ? 'var(--orange)' : undefined, fontWeight: i.warning_count > 0 ? 600 : undefined }}>{i.warning_count}</td>
                <td>{i.suspension_next_semester ? <span style={{ color: 'var(--red)', fontWeight: 700 }}>YES</span> : 'No'}</td>
                <td>{Number(i.rating_average || 0).toFixed(2)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>

      {/* APPLICATIONS */}
      <div className="panel">
        <div className="panel-title">Visitor Applications ({data.applications.length})</div>
        {data.applications.length === 0 ? <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>No applications.</p> : (
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Type</th><th>GPA</th><th>Justification</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>{data.applications.map(a => (
                <tr key={a.application_id}>
                  <td>{a.applicant_name}</td>
                  <td style={{ fontSize: '0.75rem' }}>{a.email}</td>
                  <td>{a.application_type}</td>
                  <td>{a.prior_gpa ? Number(a.prior_gpa).toFixed(2) : '—'}</td>
                  <td style={{ fontSize: '0.78rem', maxWidth: 220 }}>{a.justification || '—'}</td>
                  <td><span style={{ fontWeight: 600, color: a.status==='approved' ? 'var(--green)' : a.status==='rejected' ? 'var(--red)' : 'var(--orange)' }}>{a.status}</span></td>
                  <td>{a.status === 'pending' ? (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn-primary btn-sm" onClick={() => act(`/registrar/application/${a.application_id}`, { decision: 'approved' })}>Approve</button>
                      <button className="btn-secondary btn-sm" onClick={() => act(`/registrar/application/${a.application_id}`, { decision: 'rejected' })}>Reject</button>
                    </div>
                  ) : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>

      {/* GENERAL COMPLAINTS */}
      <div className="panel">
        <div className="panel-title">General Complaints ({generalComplaints.length})</div>
        {generalComplaints.length === 0 ? <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>No general complaints.</p> : (
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>Filed By</th><th>Against</th><th>Description</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>{generalComplaints.map(c => (
                <tr key={c.complaint_id}>
                  <td>{c.filer_name}</td>
                  <td>{c.target_name}</td>
                  <td style={{ fontSize: '0.78rem', maxWidth: 260 }}>{c.complaint_text}</td>
                  <td><span style={{ fontWeight: 600, color: c.status==='resolved' ? 'var(--green)' : c.status==='open' ? 'var(--orange)' : 'var(--muted)' }}>{c.status.replace('_',' ')}</span></td>
                  <td>{['open','under_review'].includes(c.status) ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <input placeholder="Resolution note" id={`note-${c.complaint_id}`} style={{ padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, fontSize: '0.75rem', minWidth: 150, fontFamily: 'inherit' }} />
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="btn-primary btn-sm" onClick={() => act(`/registrar/complaint/${c.complaint_id}`, { action: 'resolve', resolution_note: document.getElementById(`note-${c.complaint_id}`)?.value })}>Resolve</button>
                        <button className="btn-secondary btn-sm" onClick={() => act(`/registrar/complaint/${c.complaint_id}`, { action: 'dismiss', resolution_note: '' })}>Dismiss</button>
                      </div>
                    </div>
                  ) : <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{c.resolution_note || '—'}</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>

      {/* GRADUATION APPS */}
      <div className="panel">
        <div className="panel-title">Graduation Applications ({data.grad_apps.length})</div>
        {data.grad_apps.length === 0 ? <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>No graduation applications.</p> : (
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>Student</th><th>GPA</th><th>Submitted</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>{data.grad_apps.map(g => (
                <tr key={g.graduation_app_id}>
                  <td>{g.student_name}</td>
                  <td style={{ color: 'var(--green)', fontWeight: 600 }}>{Number(g.cumulative_gpa).toFixed(3)}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{g.submitted_at?.slice(0,10)}</td>
                  <td><span style={{ fontWeight: 600, color: g.decision_status==='approved' ? 'var(--green)' : g.decision_status==='rejected' ? 'var(--red)' : 'var(--orange)' }}>{g.decision_status}</span></td>
                  <td>{g.decision_status === 'pending' ? (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn-primary btn-sm" onClick={() => act(`/registrar/graduation/${g.graduation_app_id}`, { decision: 'approved' })}>Approve</button>
                      <button className="btn-secondary btn-sm" onClick={() => act(`/registrar/graduation/${g.graduation_app_id}`, { decision: 'rejected' })}>Reject</button>
                    </div>
                  ) : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
